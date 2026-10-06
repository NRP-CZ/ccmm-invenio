#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm location <-> RDM locations (GeoJSON features, WGS84)."""

from __future__ import annotations

import json
import logging
from typing import Any, cast, override

import pygml
import shapely
import shapely.geometry
import shapely.wkt
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocab_service
from lxml.etree import fromstring
from marshmallow import ValidationError, fields
from pyproj import CRS, Transformer
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
from shapely.ops import transform
from xmlschema.utils.qnames import get_namespace

from ccmm_invenio.resources.serializers.ccmm.converter import NS_GML
from ccmm_invenio.resources.serializers.ccmm.schema.identifiers import IdentifierSchema
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField

log = logging.getLogger(__name__)


WGS84 = "http://www.opengis.net/def/crs/EPSG/0/4326"
"""srsName of the geometries dumped to ccmm (as wkt)."""


LOCATION_RELATIONS = CCMMVocabularyField("locationrelations")
"""ccmm location relation type <-> locationrelations vocabulary item."""


def _to_wgs84(geometry: BaseGeometry, srs_name: str | None) -> BaseGeometry:
    """Reproject the geometry to WGS84 (longitude, latitude) - GeoJSON coordinates."""
    if not srs_name:
        return geometry
    crs = CRS.from_user_input(srs_name)
    if crs.to_epsg() == 4326:  # noqa: PLR2004
        return geometry
    # coordinates are x (easting, longitude) first - pygml already swapped the lat/lon axis order of gml
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    return transform(transformer.transform, geometry)


def _load_gml(xml: str, tag: str | None = None) -> BaseGeometry:
    """Parse a gml geometry (serialized xml, see XMLToGenericJSONConverter) to WGS84."""
    element = fromstring(xml.encode("utf-8"))
    if tag:
        element.tag = tag
    return _to_wgs84(shape(cast("Any", pygml.parse(element).__geo_interface__)), element.get("srsName"))


def _load_location_geometries(location: dict[str, Any]) -> list[BaseGeometry]:
    """Return the geometries of a ccmm location in WGS84.

    The ccmm geometry is a single geometry in several representations - the wkt is used, otherwise the gml.
    The bounding boxes are bounding boxes of the geometry, so they are used only without a geometry.
    """
    geometry = location.get("geometry") or {}
    if wkt := geometry.get("wkt"):
        # ponytail: wkt is taken as longitude latitude (the usual practice) even for EPSG:4326,
        # whose official axis order is latitude longitude
        return [_to_wgs84(shapely.wkt.loads(wkt["$"]), wkt.get("srsName"))]
    gml = [value for key, value in geometry.items() if get_namespace(key) == NS_GML]
    if gml:
        return [_load_gml(gml[0])]
    return [_load_gml(bbox, f"{{{NS_GML}}}Envelope") for bbox in location.get("bounding_box", [])]


def _rdm_geometries(geometry: BaseGeometry) -> list[dict[str, Any]]:
    """Convert to GeoJSON geometries RDM accepts (Point, MultiPoint, Polygon) - multi-polygons are split."""
    geometry = shapely.make_valid(geometry)
    if geometry.geom_type in ("Point", "MultiPoint", "Polygon"):
        return [json.loads(shapely.to_geojson(geometry))]
    if isinstance(geometry, BaseMultipartGeometry):  # MultiPolygon, GeometryCollection
        return [rdm_geometry for part in geometry.geoms for rdm_geometry in _rdm_geometries(part)]
    log.warning("Skipping a %s location geometry, RDM supports only Point, MultiPoint and Polygon", geometry.geom_type)
    return []


class LocationsField(fields.Field):
    """ccmm locations <-> RDM locations ({"features": [...]}).

    A ccmm location becomes one RDM feature per geometry (a multi-polygon is split to polygons,
    as RDM does not accept them), all of them with the same:

    * place - the names of the location, joined by "; "
    * identifiers - the location iri and the related objects, only of the RDM location schemes
      (RDM_RECORDS_LOCATION_SCHEMES, e.g. wikidata, geonames)
    * description - the title of the relation type (e.g. "Collected in")

    On dump, each RDM feature is a ccmm location, the geometry as wkt in WGS84 - the features
    of a single ccmm location are not grouped back.
    Not mapped: the label of the geometry.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, list):
            raise ValidationError("Expected a list of locations")
        features = [feature for location in value for feature in self._load_location(location)]
        return {"features": features} if features else None

    def _load_location(self, location: dict[str, Any]) -> list[dict[str, Any]]:
        allowed_schemes = current_app.config["RDM_RECORDS_LOCATION_SCHEMES"]
        identifiers = [
            identifier for identifier in self._load_identifiers(location) if identifier["scheme"] in allowed_schemes
        ]
        common = {
            "place": "; ".join(location.get("name", [])),
            "identifiers": [i for idx, i in enumerate(identifiers) if i not in identifiers[:idx]],
            "description": self._load_relation_type(location.get("relation_type")),
        }
        common = {key: value for key, value in common.items() if value}
        geometries = [
            rdm_geometry
            for geometry in _load_location_geometries(location)
            for rdm_geometry in _rdm_geometries(geometry)
        ]
        if geometries:
            return [{"geometry": geometry, **common} for geometry in geometries]
        return [common] if common else []

    @staticmethod
    def _load_identifiers(location: dict[str, Any]) -> list[dict[str, Any]]:
        """Return the identifiers of the location - its iri and the iris and identifiers of the related objects."""
        ccmm_identifiers = [{"value": iri, "iri": iri} for iri in [location.get("iri")] if iri]
        for related_object in location.get("related_object", []):
            if related_object.get("iri"):
                ccmm_identifiers.append({"value": related_object["iri"], "iri": related_object["iri"]})
            ccmm_identifiers.extend(related_object.get("identifier", []))
        return cast("list[dict[str, Any]]", IdentifierSchema(many=True).load(ccmm_identifiers))

    @staticmethod
    def _load_relation_type(relation_type: Any) -> str | None:
        """Return the title of the location relation type in the default locale."""
        if not relation_type:
            return None
        relation_id = cast("dict[str, Any]", LOCATION_RELATIONS.deserialize(relation_type))["id"]
        title = vocab_service.read(
            system_identity,
            ("locationrelations", relation_id),  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
        ).data.get("title", {})
        return title.get(current_app.config.get("BABEL_DEFAULT_LOCALE", "en")) or next(iter(title.values()), None)

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        return [self._dump_feature(feature) for feature in value.get("features", [])]

    def _dump_feature(self, feature: dict[str, Any]) -> dict[str, Any]:
        location: dict[str, Any] = {
            "relation_type": LOCATION_RELATIONS.serialize(
                "relation_type", {"relation_type": {"id": self._dump_relation_type(feature.get("description"))}}
            )
        }
        if feature.get("place"):
            location["name"] = feature["place"].split("; ")
        if feature.get("geometry"):
            geometry = shapely.geometry.shape(feature["geometry"])
            location["geometry"] = {"wkt": {"srsName": WGS84, "$": shapely.to_wkt(geometry, rounding_precision=-1)}}
        if feature.get("identifiers"):
            location["related_object"] = [
                {"identifier": [IdentifierSchema().dump(identifier)]} for identifier in feature["identifiers"]
            ]
        return location

    @staticmethod
    def _dump_relation_type(description: str | None) -> str:
        """Return the location relation type whose title is the description, "other" if there is none."""
        if description:
            for relation in vocab_service.search(system_identity, type="locationrelations").hits:
                if description in relation.get("title", {}).values():
                    return cast("str", relation["id"])
        return "other"

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import shapely
import yaml
from invenio_access.permissions import system_identity
from invenio_rdm_records.services.schemas.metadata import FeatureSchema
from invenio_vocabularies.proxies import current_service as vocab_service
from shapely.geometry import shape

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    NS_GML,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.locations import WGS84

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLE = (
    Path(__file__).parent.parent
    / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml/ccmm_sample.xml"
)
COLLECTED = {"iri": "https://vocabs.ccmm.cz/registry/codelist/LocationRelation/Collected"}
schema = DatasetMetadataSchema(only=("locations",))


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    for vocabulary_type, pid_type in (("identifierschemes", "idsch"), ("locationrelations", "locrel")):
        vocab_service.create_type(system_identity, vocabulary_type, pid_type)
        for entry in yaml.safe_load((FIXTURES / f"{vocabulary_type}.yaml").read_text(encoding="utf-8")):
            vocab_service.create(system_identity, {"type": vocabulary_type, **entry})
    vocab_service.indexer.refresh()


@pytest.fixture(scope="module")
def sample_location() -> dict:
    data, errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    assert errors == []
    return data["location"][0]


def load_features(*locations: dict) -> list:
    return schema.load({"location": list(locations)})["locations"]["features"]


def test_ccmm_sample(vocabularies, sample_location):
    (feature,) = load_features(sample_location)

    # the wkt of the geometry - the gml is the same geometry, the bounding box is derived from it
    assert feature["geometry"]["type"] == "Polygon"
    assert shape(feature["geometry"]).equals(shapely.wkt.loads(sample_location["geometry"]["wkt"]["$"]))
    assert feature["place"] == "Středočeský kraj"
    assert feature["description"] == "Collected in"
    # the related object is a RÚIAN url - not in the identifierschemes vocabulary, so a "url" identifier
    assert feature["identifiers"] == [{"identifier": "https://vdp.cuzk.gov.cz/vdp/ruian/vusc/27", "scheme": "url"}]
    assert FeatureSchema().validate({"features": [feature]}) == {}


def test_gml_is_reprojected(vocabularies, sample_location):
    gml_only = copy.deepcopy(sample_location)
    del gml_only["geometry"]["wkt"]
    (feature,) = load_features(gml_only)

    # gml in EPSG:5514 reprojected to WGS84 - the same polygon as the wkt (up to the rounding of the gml)
    wkt_polygon = shapely.wkt.loads(sample_location["geometry"]["wkt"]["$"])
    assert shape(feature["geometry"]).symmetric_difference(wkt_polygon).area / wkt_polygon.area < 1e-6


def test_bounding_box_without_geometry(vocabularies, sample_location):
    bbox_only = {"bounding_box": sample_location["bounding_box"], "relation_type": COLLECTED}
    (feature,) = load_features(bbox_only)
    assert feature["geometry"]["type"] == "Polygon"
    assert shape(feature["geometry"]).bounds == pytest.approx((13.4115, 49.5041, 15.5246, 50.6184), abs=1e-4)


def test_multipolygon_is_split(vocabularies):
    location = {
        "name": ["Two islands"],
        "relation_type": COLLECTED,
        "geometry": {
            "wkt": {
                "srsName": WGS84,
                "$": "MULTIPOLYGON (((14 50, 15 50, 15 51, 14 50)), ((16 50, 17 50, 17 51, 16 50)))",
            }
        },
        # a wikidata identifier is a RDM location identifier
        "related_object": [
            {"identifier": [{"value": "Q193071", "scheme": {"iri": "https://www.wikidata.org/entity/"}}]}
        ],
    }
    features = load_features(location)
    assert [feature["geometry"]["type"] for feature in features] == ["Polygon", "Polygon"]
    for feature in features:
        assert feature["place"] == "Two islands"
        assert feature["identifiers"] == [{"identifier": "Q193071", "scheme": "wikidata"}]
    assert FeatureSchema().validate({"features": features}) == {}


def test_url_identifier(vocabularies):
    location = {
        "name": ["A place on the web"],
        "relation_type": COLLECTED,
        # an iri of no known scheme falls back to the "url" scheme - a RDM location identifier
        "related_object": [{"iri": "https://vdp.cuzk.gov.cz/vdp/ruian/vusc/27"}],
    }
    (feature,) = load_features(location)
    assert feature["identifiers"] == [{"identifier": "https://vdp.cuzk.gov.cz/vdp/ruian/vusc/27", "scheme": "url"}]
    assert FeatureSchema().validate({"features": [feature]}) == {}


def test_line_is_skipped(vocabularies):
    location = {
        "name": ["A road"],
        "relation_type": COLLECTED,
        "geometry": {"wkt": {"$": "LINESTRING (14 50, 15 51)"}},
    }
    # RDM does not support lines - the feature has no geometry
    assert load_features(location) == [{"place": "A road", "description": "Collected in"}]


def test_round_trip(vocabularies, sample_location):
    features = load_features(sample_location)
    dumped = schema.dump({"locations": {"features": features}})["location"]

    (location,) = dumped
    assert location["geometry"]["wkt"]["srsName"] == WGS84
    assert location["relation_type"]["iri"] == COLLECTED["iri"]
    _xml, errors = XMLToGenericJSONConverter().json_to_xml(ccmm_1_1_0_schema, location, f"{{{NS_CCMM_1_1_0}}}location")
    assert errors == []

    assert load_features(*dumped) == features


def test_gml_namespace_key(sample_location):
    # the converter keeps the gml geometry under the "{namespace}local" key
    assert f"{{{NS_GML}}}MultiSurface" in sample_location["geometry"]

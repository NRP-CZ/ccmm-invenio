#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""DataCite serializer for CCMM production records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import JSONSerializer
from invenio_rdm_records.resources.serializers.datacite import DataCite43Schema

if TYPE_CHECKING:
    from collections.abc import Mapping


class CCMMProductionDataCiteJSONSerializer_1_1_0(MarshmallowSerializer):  # noqa: N801
    """Marshmallow based DataCite serializer for records."""

    def __init__(self, **options: Any):
        """Create a new instance of the serializer."""
        super().__init__(
            format_serializer_cls=JSONSerializer,
            object_schema_cls=ProductionDataCiteSchema,
            list_schema_cls=BaseListSchema,
            schema_kwargs={},
            **options,
        )


class ProductionDataCiteSchema(DataCite43Schema):
    """Schema for DataCite serialization of CCMM production records.

    TODO: this will not work correctly !!!
    """

    @override
    def get_locations(self, obj: Mapping[str, Any]) -> list:
        """Get locations from CCMM metadata and serialize to DataCite format.

        Serializes location structures into DataCite geoLocations format.
        The metadata uses the parsed format (after production_1_1_0 parser conversion):
        - place: string (converted from names[0])
        - geometry: {type, coordinates} (from geometry or bounding_boxes)
        - identifiers: array (from related_objects)

        Input structure (parsed CCMM metadata):
            {
                "locations": {
                    "features": [
                        {
                            "place": "Středočeský kraj",
                            "geometry": {"type": "Polygon", "coordinates": [...]},
                            "identifiers": [{"identifier": "...", "scheme": "url"}]
                        }
                    ]
                }
            }

        Output structure (DataCite):
            {
                "geoLocations": [
                    {
                        "geoLocationPlace": "Středočeský kraj",
                        "geoLocationBox": {
                            "westBoundLongitude": "...",
                            "eastBoundLongitude": "...",
                            "southBoundLatitude": "...",
                            "northBoundLatitude": "..."
                        }
                    }
                ]
            }
        """
        locations = []
        metadata = obj.get("metadata", {})

        # Get locations from metadata (parsed format)
        loc_list = metadata.get("locations", {}).get("features", [])
        if not loc_list:
            return []

        for location in loc_list:
            serialized_location = {}

            # Handle place name (parser converts names[0] to place)
            place = location.get("place")
            if place:
                serialized_location["geoLocationPlace"] = place

            # Handle geometry (Point or Polygon)
            geometry = location.get("geometry")
            if geometry:
                geo_type = geometry.get("type")
                coords = geometry.get("coordinates", [])

                if geo_type == "Point" and len(coords) >= 2:
                    # Point geometry - use as geoLocationPoint
                    serialized_location["geoLocationPoint"] = {
                        "pointLongitude": str(coords[0]),
                        "pointLatitude": str(coords[1]),
                    }

                elif geo_type == "Polygon" and coords:
                    # Polygon geometry - check if it forms a bounding box
                    # Polygon coordinates are typically wrapped in an outer array
                    polygon_coords = coords[0] if isinstance(coords[0], list) else coords

                    # Check if this is a simple rectangular box (4 or 5 points)
                    if len(polygon_coords) in [4, 5]:
                        x_coords = set()
                        y_coords = set()
                        for coord in polygon_coords:
                            if len(coord) >= 2:
                                x_coords.add(coord[0])
                                y_coords.add(coord[1])

                        # If we have exactly 2 distinct X and 2 distinct Y values, it's a box
                        if len(x_coords) == 2 and len(y_coords) == 2:
                            x_sorted = sorted(x_coords)
                            y_sorted = sorted(y_coords)
                            serialized_location["geoLocationBox"] = {
                                "westBoundLongitude": str(x_sorted[0]),
                                "eastBoundLongitude": str(x_sorted[1]),
                                "southBoundLatitude": str(y_sorted[0]),
                                "northBoundLatitude": str(y_sorted[1]),
                            }
                        else:
                            # Irregular polygon - serialize as polygon points
                            polygon = []
                            for coord in polygon_coords:
                                if len(coord) >= 2:
                                    polygon.append(
                                        {
                                            "polygonPoint": {
                                                "pointLongitude": str(coord[0]),
                                                "pointLatitude": str(coord[1]),
                                            }
                                        }
                                    )
                            if polygon:
                                serialized_location["geoLocationPolygon"] = polygon

            # Only add if we have at least some location data
            if serialized_location:
                locations.append(serialized_location)

        return locations or []

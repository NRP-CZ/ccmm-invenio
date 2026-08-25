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

import json
from typing import TYPE_CHECKING, Any, override

from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import JSONSerializer
from invenio_rdm_records.resources.serializers.datacite import DataCite43Schema

if TYPE_CHECKING:
    from collections.abc import Mapping

# Load SPDX licenses from commonmeta package using importlib.resources
try:
    from importlib import resources

    _SPDX_FILE = (
        resources.files("commonmeta") / "resources" / "spdx" / "licenses.json"
    )
    with _SPDX_FILE.open(encoding="utf-8") as f:
        _spdx_data = json.load(f)
    # Create lookup dict with lowercase keys for case-insensitive matching
    _SPDX_LOOKUP = {lic["licenseId"].lower(): lic for lic in _spdx_data.get("licenses", [])}
except Exception:
    # Fallback if commonmeta is not available
    _SPDX_LOOKUP = {}

# CCMM-specific license ID to SPDX ID mapping (values are case-sensitive SPDX IDs)
_CCMM_TO_SPDX = {
    "cc-4.0": "CC-BY-4.0",
    "apache-2.0": "Apache-2.0",
    "gpl-3.0": "GPL-3.0-only",
}

# SPDX license list scheme URI
_SPDX_SCHEME_URI = "https://spdx.org/licenses/"


def _get_spdx_license(license_id: str) -> dict[str, str] | None:
    """Get SPDX license info (identifier and URI) for a given license ID.

    Args:
        license_id: CCMM or SPDX license identifier

    Returns:
        Dict with 'identifier', 'uri', and 'schemeUri' keys, or None if not found
    """
    if not license_id:
        return None

    license_id_lower = license_id.lower()

    # Try direct SPDX lookup first (case-insensitive)
    if license_id_lower in _SPDX_LOOKUP:
        lic = _SPDX_LOOKUP[license_id_lower]
        return {
            "identifier": lic["licenseId"],
            "uri": lic["seeAlso"][0],
            "schemeUri": _SPDX_SCHEME_URI,
        }

    # Try CCMM to SPDX mapping (case-insensitive)
    spdx_id = _CCMM_TO_SPDX.get(license_id_lower)
    if spdx_id and spdx_id.lower() in _SPDX_LOOKUP:
        lic = _SPDX_LOOKUP[spdx_id.lower()]
        return {
            "identifier": lic["licenseId"],
            "uri": lic["seeAlso"][0],
            "schemeUri": _SPDX_SCHEME_URI,
        }

    return None


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
        """Get locations."""
        return []

    @override
    def get_rights(self, obj: Mapping[str, Any]) -> list:
        """Get rights (licenses) and enrich with SPDX information.

        Serializes rights from metadata, enriching common licenses with
        SPDX identifiers and URIs for better FAIR compliance.

        Input structure:
            {
                "rights": [
                    {
                        "id": "CC-4.0",
                        "title": {"en": "version 4.0 International License"},
                        "props": {"url": "..."}
                    }
                ]
            }

        Output structure:
            {
                "rightsList": [
                    {
                        "rights": "Creative Commons Attribution 4.0 International",
                        "rightsIdentifier": "cc-by-4.0",
                        "rightsIdentifierScheme": "SPDX",
                        "rightsUri": "https://creativecommons.org/licenses/by/4.0/"
                    }
                ]
            }
        """
        rights = obj.get("metadata", {}).get("rights", [])
        if not rights:
            return []

        result = []

        for right in rights:
            # Get title for the rights text
            title = right.get("title", {})
            rights_text = title.get("en") or title.get("cs") or ""

            entry = {"rights": rights_text}

            # Get license ID
            license_id = right.get("id")

            # Check if we have SPDX mapping for this license
            spdx_info = _get_spdx_license(license_id)
            if spdx_info:
                entry["rightsIdentifier"] = spdx_info["identifier"]
                entry["rightsIdentifierScheme"] = "SPDX"
                entry["rightsUri"] = spdx_info["uri"]
                entry["schemeUri"] = spdx_info["schemeUri"]
            else:
                # Fall back to vocabulary props or existing data
                if license_id:
                    entry["rightsIdentifier"] = license_id

                # Try to get scheme from props
                props = right.get("props", {})
                if props.get("scheme"):
                    entry["rightsIdentifierScheme"] = props.get("scheme")

                # Try to get URL from props or link
                url = props.get("url") or right.get("link", {})
                if url:
                    entry["rightsUri"] = url

            # Add copyright if present
            copyright_info = right.get("copyright", {})
            if copyright_info:
                copyright_text = copyright_info.get("text", "")
                if copyright_text and not rights_text:
                    entry["rights"] = copyright_text

            if entry.get("rights"):  # Only add if we have at least the rights text
                result.append(entry)

        return result

#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""DataCite serializer for CCMM NMA records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import JSONSerializer
from invenio_rdm_records.resources.serializers.datacite import DataCite43Schema
from invenio_rdm_records.resources.serializers.datacite.schema import get_preferred_identifier

if TYPE_CHECKING:
    from collections.abc import Mapping

# Preferred funder identifier schemes in order of preference
PREFERRED_FUNDER_SCHEMES = ("ror", "doi", "grid", "isni", "gnd")

# Map scheme names to DataCite funder identifier types
FUNDER_SCHEME_MAPPING = {
    "ROR": "ROR",
    "DOI": "Crossref Funder ID",
    "GRID": "GRID",
    "ISNI": "ISNI",
    "GND": "GND",
}


def _get_award_title(title: str | dict | None) -> str | None:
    """Extract award title, handling both string and localized dict formats."""
    if not title:
        return None
    if isinstance(title, dict):
        return title.get("en") or next(iter(title.values()), None)
    return title


class CCMMNMADataCiteJSONSerializer_1_1_0(MarshmallowSerializer):  # noqa: N801
    """Marshmallow based DataCite serializer for records."""

    def __init__(self, **options: Any):
        """Create a new instance of the serializer."""
        super().__init__(
            format_serializer_cls=JSONSerializer,
            object_schema_cls=NMADataCiteSchema,
            list_schema_cls=BaseListSchema,
            schema_kwargs={},
            **options,
        )


class NMADataCiteSchema(DataCite43Schema):
    """Schema for DataCite serialization of CCMM production records.

    TODO: this will not work correctly !!!
    """

    @override
    def get_locations(self, obj: Mapping[str, Any]) -> list:
        """Get locations."""
        return []

    def get_funding(self, obj: Mapping[str, Any]) -> list:
        """Get funding references from CCMM metadata.

        Maps both CCMM 'funding_references' and standard Invenio 'funding' structures
        to DataCite fundingReferences format.
        """
        from marshmallow import missing

        metadata = obj.get("metadata", {})
        funding_list = metadata.get("funding_references") or metadata.get("funding", [])
        if not funding_list:
            return missing

        funding_references = []

        for funding in funding_list:
            # Normalize: support both CCMM (funders array) and Invenio (funder object) structures
            funders = funding.get("funders", [])
            funder_obj = funding.get("funder", {})

            # Use first funder if available, skip if none
            funder = funders[0] if funders else funder_obj
            if not funder:
                continue

            funding_ref = {"funderName": funder.get("name", "")}

            # Get funder identifier using invenio's helper
            funder_ids = funder.get("identifiers", [])
            if funder_ids:
                identifier = get_preferred_identifier(PREFERRED_FUNDER_SCHEMES, funder_ids)
                if identifier:
                    scheme = identifier.get("scheme", "Other")
                    id_value = identifier.get("value") or identifier.get("identifier", "")
                    funding_ref["funderIdentifier"] = id_value
                    funding_ref["funderIdentifierType"] = FUNDER_SCHEME_MAPPING.get(
                        scheme.upper() if scheme else "Other", "Other"
                    )

            # Normalize award data from both CCMM and Invenio structures
            award_iri = funding.get("iri")
            award_number = funding.get("local_identifier")
            award_title_raw = funding.get("award_title")

            award = funding.get("award", {})
            if award:
                if not award_title_raw:
                    award_title_raw = award.get("title")
                if not award_number:
                    award_number = award.get("number")
                if not award_iri:
                    award_ids = award.get("identifiers", [])
                    if award_ids:
                        award_iri = award_ids[0].get("identifier")

            # Add award details if present
            if award_title_raw:
                title = _get_award_title(award_title_raw)
                if title:
                    funding_ref["awardTitle"] = title

            if award_number:
                funding_ref["awardNumber"] = award_number

            if award_iri:
                funding_ref["awardURI"] = award_iri

            if funding_ref.get("funderName"):
                funding_references.append(funding_ref)

        return funding_references or missing

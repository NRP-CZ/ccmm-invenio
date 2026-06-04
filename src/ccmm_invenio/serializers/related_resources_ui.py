#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""UI serialization schemas for CCMM related resources."""

from __future__ import annotations

from functools import partial
from typing import Any

from invenio_rdm_records.resources.serializers.ui.schema import (
    AdditionalDescriptionsSchema,
    AdditionalTitlesSchema,
    DatesSchema,
    FundingSchema,
    LocationSchema,
    RightsSchema,
)
from invenio_rdm_records.resources.serializers.ui.schema import (
    make_affiliation_index as rdm_make_affiliation_index,
)
from invenio_vocabularies.resources import VocabularyL10Schema
from marshmallow import Schema, fields
from marshmallow_utils.fields import FormatEDTF


def make_related_affiliation_index(attr: str, obj: dict, *args: Any) -> Any:
    """Build an RDM affiliation index for a nested related resource."""
    return rdm_make_affiliation_index(attr, {"metadata": obj}, *args)


class IdentifierSchema(Schema):
    """UI schema for related resource identifiers."""

    identifier = fields.String()
    scheme = fields.String()


class CCMMRelatedResourceUISchema(Schema):
    """UI schema for a single CCMM related resource."""

    title = fields.String()
    publisher = fields.String()
    publication_date = fields.String()

    publication_date_l10n_short = FormatEDTF(attribute="publication_date", format="short")
    publication_date_l10n_medium = FormatEDTF(attribute="publication_date", format="medium")
    publication_date_l10n_long = FormatEDTF(attribute="publication_date", format="long")
    publication_date_l10n_full = FormatEDTF(attribute="publication_date", format="full")

    identifiers = fields.List(fields.Nested(IdentifierSchema))

    resource_type = fields.Nested(VocabularyL10Schema)
    relation_type = fields.Nested(VocabularyL10Schema)
    languages = fields.List(fields.Nested(VocabularyL10Schema))

    additional_titles = fields.List(fields.Nested(AdditionalTitlesSchema))
    additional_descriptions = fields.List(fields.Nested(AdditionalDescriptionsSchema))
    dates = fields.List(fields.Nested(DatesSchema))
    funding = fields.List(fields.Nested(FundingSchema))
    rights = fields.List(fields.Nested(RightsSchema))
    locations = fields.Nested(LocationSchema)

    creators = fields.Function(partial(make_related_affiliation_index, "creators"))
    contributors = fields.Function(partial(make_related_affiliation_index, "contributors"))

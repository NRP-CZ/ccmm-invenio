#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm funding reference <-> RDM funding item (funder and award)."""

from __future__ import annotations

from typing import Any, override

from flask import current_app
from marshmallow import EXCLUDE, Schema, ValidationError, fields
from marshmallow_utils.fields import SanitizedUnicode

from ccmm_invenio.resources.serializers.ccmm.schema.identifiers import (
    AwardIdentifiersField,
    IdentifierSchema,
    service_item_exists,
)


class FunderField(fields.Field):
    """ccmm funder (an agent - organization or person) <-> RDM funder.

    Expects a single funder (a list with a single item), use it with SplitNested.
    RDM funder has a name (free text) and an id from the funders vocabulary (invenio FunderRelationSchema).
    The id is set when the ROR of the agent is in the funders vocabulary, other identifiers have
    no counterpart in RDM and are dropped. On dump, the id is the ROR identifier of the organization.
    A person is a funder by name, as RDM does not distinguish persons and organizations here -
    on dump, a funder is always an organization.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
            raise ValidationError("Expected a single funder, use SplitNested")
        agent = value[0].get("organization") or value[0].get("person")
        if not agent:
            raise ValidationError("Expected an organization or a person")
        funder: dict[str, Any] = {"name": agent.get("name")}
        identifiers = IdentifierSchema(many=True).load(agent.get("identifier", [])) or []
        ror = next((identifier["identifier"] for identifier in identifiers if identifier["scheme"] == "ror"), None)
        if ror and service_item_exists("funders", ror):
            funder["id"] = ror
        return funder

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        organization: dict[str, Any] = {"name": value.get("name")}
        if value.get("id"):
            organization["identifier"] = IdentifierSchema(many=True).dump(
                [{"identifier": value["id"], "scheme": "ror"}]
            )
        return [{"organization": organization}]


class AwardTitleField(fields.Field):
    """ccmm award title (a plain string, no language) <-> RDM award title (i18n dict).

    The language of the ccmm title is not known, the default locale (BABEL_DEFAULT_LOCALE) is used.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        return {current_app.config.get("BABEL_DEFAULT_LOCALE", "en"): value}

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        return value.get(current_app.config.get("BABEL_DEFAULT_LOCALE", "en")) or next(iter(value.values()))


class FundingReferenceSchema(Schema):
    """CCMM funding reference <-> RDM funding item (funder and award).

    Expects a single funder, use it with SplitNested (one RDM funding item per ccmm funder,
    sharing the award). Types as in invenio_vocabularies.contrib.awards.schema.FundingRelationSchema.
    The award is not looked up in the awards vocabulary, it is always a free-text one.
    """

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 1..n, here a single one
    funder = FunderField(required=True)

    # ccmm 0..1
    award_number = SanitizedUnicode(data_key="local_identifier", attribute="award.number")

    # ccmm 0..1, a plain string
    award_title = AwardTitleField(data_key="award_title", attribute="award.title")

    # ccmm 0..1; the iri of the funding reference, e.g. the web page of the grant
    award_identifiers = AwardIdentifiersField(data_key="iri", attribute="award.identifiers")

    # ccmm 0..1, anyURI; RDM program is a string
    award_program = SanitizedUnicode(data_key="funding_program", attribute="award.program")

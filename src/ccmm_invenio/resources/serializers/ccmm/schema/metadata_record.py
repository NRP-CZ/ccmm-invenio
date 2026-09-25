#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm metadata_identification (metadata_record) of a dataset.

A harvested (3rd party) dataset keeps the metadata records of its source in
metadata.metadata_identifications (CCMMInvenioMetadataRecord in the model, see MetadataRecordSchema)
and they are dumped without changes. A dataset created here has none - its metadata record is made
from the technical metadata of the invenio record (see metadata_records).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app
from marshmallow import EXCLUDE, Schema, fields

from ccmm_invenio.resources.serializers.ccmm.schema.agents import ContributorSchema
from ccmm_invenio.resources.serializers.ccmm.schema.fields import ApplicationProfileSchema, IriLabelSchema
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField

CCMM_STANDARD = {"iri": "https://schema.ccmm.cz/research-data/1.1.0", "label": [{"lang": "en", "$": "CCMM RD 1.1.0"}]}

DATA_MANAGER_ROLE = "datamanager"
"""The contributor role (contributorsroles) of the ccmm Data Manager."""


class MetadataRecordSchema(Schema):
    """ccmm metadata record <-> CCMMInvenioMetadataRecord of the model.

    The agents (qualified_relation) are RDM contributors, as the dataset contributors
    (see ContributorSchema); the fields are declared in the order of the ccmm xsd.
    """

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 0..1
    iri = fields.String()

    # ccmm 0..n
    languages = fields.List(CCMMVocabularyField("languages"), data_key="language")

    # ccmm 1..n, at least one Data Manager
    qualified_relations = fields.List(fields.Nested(ContributorSchema), required=True, data_key="qualified_relation")

    # ccmm 0..n, xs:date
    date_updated = fields.List(fields.String())

    # ccmm 0..1, xs:date
    date_created = fields.String()

    # ccmm 1..n
    conforms_to_standards = fields.List(fields.Nested(ApplicationProfileSchema), data_key="conforms_to_standard")

    # ccmm 1..1, iri and a multilingual label
    original_repository = fields.Nested(IriLabelSchema, required=True)


def metadata_records(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the ccmm metadata records (generic json) of an invenio record.

    The stored ones (a harvested dataset) without changes, otherwise one made from the technical
    metadata of the record (see generated_metadata_record).
    """
    if stored := (record.get("metadata") or {}).get("metadata_identifications"):
        return MetadataRecordSchema(many=True).dump(stored)
    return [generated_metadata_record(record)]


def generated_metadata_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return the ccmm metadata record (generic json) of a dataset created here.

    record has the technical metadata of the invenio record: created, updated (ISO strings
    or datetimes), links (self - the metadata of the record) and its metadata.

    iri                  - links.self, the metadata of the record in this repository
    qualified_relation   - the contributors with the Data Manager role (they stay among the
                           contributors of the dataset as well); when there are none, this repository
                           (THEME_SITENAME) as the Data Manager - not the owners of the record, the export
                           is public and harvested, their personal data are not in it
    date_created         - created
    date_updated         - updated
    conforms_to_standard - CCMM RD 1.1.0
    original_repository  - this repository (SITE_UI_URL)
    language             - not known, not dumped
    """
    site_name = str(current_app.config.get("THEME_SITENAME") or "")
    site_url = current_app.config["SITE_UI_URL"]
    contributors = (record.get("metadata") or {}).get("contributors") or []
    data_managers = [c for c in contributors if (c.get("role") or {}).get("id") == DATA_MANAGER_ROLE] or [
        {"person_or_org": {"type": "organizational", "name": site_name or site_url}, "role": {"id": DATA_MANAGER_ROLE}}
    ]
    ret: dict[str, Any] = {}
    if iri := (record.get("links") or {}).get("self"):
        ret["iri"] = iri
    ret["qualified_relation"] = ContributorSchema().dump(data_managers, many=True)
    if updated := _date(record.get("updated")):
        ret["date_updated"] = [updated]
    if created := _date(record.get("created")):
        ret["date_created"] = created
    ret["conforms_to_standard"] = [CCMM_STANDARD]
    ret["original_repository"] = {"iri": site_url}
    if site_name:
        ret["original_repository"]["label"] = [{"lang": "en", "$": site_name}]
    return ret


def _date(value: str | datetime | None) -> str | None:
    """Return the date (xs:date) of an ISO datetime string or a datetime."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value[:10] if value else None

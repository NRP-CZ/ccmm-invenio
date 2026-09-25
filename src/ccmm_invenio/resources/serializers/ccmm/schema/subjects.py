#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm subject <-> RDM subject (vocabulary item or keyword)."""

from __future__ import annotations

from typing import Any, cast

from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_records_resources.proxies import current_service_registry
from invenio_search.engine import dsl
from invenio_vocabularies.records.models import VocabularyScheme
from marshmallow import EXCLUDE, Schema, fields, post_dump, post_load, validate


def _subject_id(iri: str) -> str | None:
    """Return the id of the subject with the iri among its identifiers, None if it is not in the vocabulary."""
    hits = cast("Any", current_service_registry.get("subjects")).search(
        system_identity, extra_filter=dsl.Q("term", **{"identifiers.identifier": iri})
    )
    return next((hit["id"] for hit in hits), None)


class SubjectSchema(Schema):
    """CCMM subject <-> RDM subject.

    Expects a single language variant of the title, use it with SplitNested(unique=True).
    A subject whose iri is in the subjects vocabulary (among the identifiers of a subject)
    becomes {"id": ...}, otherwise it is a keyword {"subject": <title>} - RDM keywords have no
    language, so there is one keyword per language variant of the title.
    Types as in invenio_vocabularies.contrib.subjects.schema.SubjectRelationSchema.
    """

    class Meta:
        """Schema options."""

        # definition (0..n), classification_code (0..1), subject_scheme (0..1): not stored in the record,
        # for a vocabulary subject they are dumped from the vocabulary (apart from the definition, see to_ccmm)
        unknown = EXCLUDE

    # ccmm 0..1; used for the vocabulary lookup, a keyword loses it
    iri = fields.String(load_only=True)

    # ccmm 1..n with xml:lang, here exactly one
    title = fields.List(fields.Dict(), load_only=True, required=True, validate=validate.Length(equal=1))

    # invenio, see to_ccmm
    id = fields.String(dump_only=True)
    subject = fields.String(dump_only=True)

    @post_load
    def to_rdm(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Convert to the vocabulary subject or a keyword."""
        if data.get("iri") and (subject_id := _subject_id(data["iri"])):
            return {"id": subject_id}
        return {"subject": data["title"][0]["$"]}

    @post_dump
    def to_ccmm(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Convert the vocabulary subject (iri, title and scheme from the vocabulary) or a keyword."""
        if not data.get("id"):
            # the language of a keyword is not known
            return {"title": [{"lang": "", "$": data["subject"]}]}
        vocabulary_subject = (
            cast("Any", current_service_registry.get("subjects")).read(system_identity, data["id"]).data
        )
        ccmm: dict[str, Any] = {
            "title": [{"lang": lang, "$": text} for lang, text in vocabulary_subject.get("title", {}).items()]
            or [{"lang": "", "$": vocabulary_subject["subject"]}],
        }
        if iri := next(
            (i["identifier"] for i in vocabulary_subject.get("identifiers", []) if i["scheme"] == "url"), None
        ):
            ccmm["iri"] = iri
        # the code in the scheme (props.classification_code), or the id without the scheme prefix
        # (ford:10509 -> 10509)
        if code := (vocabulary_subject.get("props") or {}).get("classification_code") or data["id"].partition(":")[2]:
            ccmm["classification_code"] = code
        scheme = (
            db.session.get(VocabularyScheme, {"id": vocabulary_subject["scheme"], "parent_id": "subjects"})
            if vocabulary_subject.get("scheme")
            else None
        )
        if scheme_uri := getattr(scheme, "uri", None):
            ccmm["subject_scheme"] = {"iri": scheme_uri}
            # the scheme has a single (english) name
            if scheme_name := getattr(scheme, "name", None):
                ccmm["subject_scheme"]["label"] = [{"lang": "en", "$": scheme_name}]
        return ccmm

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm identifiers (identifier/scheme, award identifiers) and the vocabulary existence checks."""

from __future__ import annotations

from typing import Any, cast, override

from flask import current_app
from idutils.detectors import detect_identifier_schemes
from idutils.normalizers import normalize_pid, to_url
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import EXCLUDE, Schema, ValidationError, fields, missing, post_load
from marshmallow_utils.fields import SanitizedUnicode
from sqlalchemy.exc import NoResultFound

from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField


class IdentifierSchemeField(CCMMVocabularyField):
    """ccmm identifier scheme (identifierschemes vocabulary) <-> RDM identifier scheme (the vocabulary id).

    The vocabulary ids are the RDM scheme ids ("doi", "url", ...). A scheme that is not
    in the vocabulary (e.g. a local one) loads as None, see IdentifierSchema.fallback_scheme.
    """

    def __init__(self, **kwargs: Any):
        """Create the field."""
        super().__init__("identifierschemes", **kwargs)

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        try:
            return super()._deserialize(value, attr, data, **kwargs)["id"]
        except ValidationError:
            return None

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        return super()._serialize({"id": value} if value else None, attr, obj, **kwargs)


class IdentifierSchema(Schema):
    """CCMM identifier <-> RDM identifier.

    Types as in marshmallow_utils.schemas.IdentifierSchema. The identifier is not validated
    against its scheme here, invenio does that when the record is stored.
    """

    class Meta:
        """Schema options."""

        # authorized (0..1): no counterpart in invenio
        unknown = EXCLUDE

    # ccmm 1..1
    identifier = SanitizedUnicode(required=True, data_key="value")

    # ccmm 1..1
    scheme = IdentifierSchemeField(data_key="scheme")

    # ccmm 0..1; on load used only for an unknown scheme (see fallback_scheme),
    # on dump derived from the identifier and scheme (omitted for schemes without an url, e.g. "other")
    iri = fields.Method(serialize="dump_iri", deserialize="load_iri")

    def load_iri(self, value: Any) -> Any:
        """Keep the ccmm iri for fallback_scheme."""
        return value

    def dump_iri(self, obj: dict[str, Any]) -> Any:
        """Return the resolvable url of the identifier, e.g. https://doi.org/10.1234/abc for a doi."""
        if not obj.get("identifier") or not obj.get("scheme"):
            return missing
        return to_url(obj["identifier"], obj["scheme"], url_scheme="https") or missing

    @post_load
    def fallback_scheme(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """For a scheme not in the vocabulary, detect the scheme from the iri, or use "other".

        https://doi.org/10.1234/abc becomes the doi 10.1234/abc, an iri of no known scheme
        is used as an url, without an iri the value is kept with the "other" scheme.
        """
        iri = data.pop("iri", None)
        if data.get("scheme") is not None:
            return data
        # the most specific scheme goes first (doi before url), url for any other iri
        detected_schemes = detect_identifier_schemes(iri) if iri else []
        if detected_schemes:
            data.update({"identifier": normalize_pid(iri, detected_schemes[0]), "scheme": detected_schemes[0]})
        else:
            data["scheme"] = "other"
        return data


def service_item_exists(service_id: str, item_id: str) -> bool:
    """Return True if the id is in the service's records (funders and affiliations have ROR ids)."""
    try:
        cast("Any", current_service_registry.get(service_id)).read(system_identity, item_id)
    except PIDDoesNotExistError, NoResultFound:  # model pids (funders, affiliations) raise NoResultFound
        return False
    return True


def vocabulary_item_exists(vocabulary_type: str, item_id: str) -> bool:
    """Return True if the item is in the vocabulary."""
    try:
        vocab_service.read(system_identity, (vocabulary_type, item_id))  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
    except PIDDoesNotExistError:
        return False
    return True


class AwardIdentifiersField(fields.Field):
    """ccmm funding reference iri <-> RDM award identifiers (schemes from VOCABULARIES_AWARD_SCHEMES).

    The scheme is detected from the iri (a doi before an url), on dump the first identifier is used.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        allowed = current_app.config["VOCABULARIES_AWARD_SCHEMES"]
        scheme = next((scheme for scheme in detect_identifier_schemes(value) if scheme in allowed), None)
        if scheme is None:
            raise ValidationError(f"Not a valid award identifier: {value}")
        return [{"identifier": normalize_pid(value, scheme), "scheme": scheme}]

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        return to_url(value[0]["identifier"], value[0]["scheme"], url_scheme="https") or None

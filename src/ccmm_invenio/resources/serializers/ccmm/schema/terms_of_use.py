#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm terms of use (license) <-> RDM rights item."""

from __future__ import annotations

from typing import Any, cast

from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_dump, post_load

from ccmm_invenio.resources.serializers.ccmm.schema.fields import SingleLocaleTextField
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField

LICENSES = CCMMVocabularyField("licenses")
"""ccmm license document <-> licenses vocabulary item."""


class TermsOfUseSchema(Schema):
    """CCMM terms of use <-> RDM rights item (a license).

    Types as in invenio_rdm_records.services.schemas.metadata.RightsSchema: a license from the
    licenses vocabulary ({"id": ...}), or a free-text one ({"title": {...}, "link": ...}).
    """

    class Meta:
        """Schema options."""

        # iri (0..1): no counterpart in invenio
        # contact_point (0..n): no counterpart in invenio
        # access_rights (1..1): not metadata in RDM, it is the record access - taken out and put
        #   back by DatasetSchema, see access.py
        unknown = EXCLUDE

    # ccmm 1..1; merged into the rights item, see merge_license
    license = fields.Method(serialize="dump_license", deserialize="load_license", required=True)

    # ccmm 0..n, multilingual; kept only for a free-text license - RDM does not accept a description
    # together with a vocabulary id, see merge_license and drop_license_description
    description = SingleLocaleTextField()

    def load_license(self, value: Any) -> dict[str, Any]:
        """Load the license from the vocabulary, or as a free-text license with the iri as the link."""
        try:
            return cast("dict[str, Any]", LICENSES.deserialize(value))
        except ValidationError:
            if not isinstance(value, dict) or not value.get("iri"):
                raise
        # not in the vocabulary; RDM requires a title - the iri when there is no label
        title = value.get("label") or [{"lang": "", "$": value["iri"]}]
        return {"link": value["iri"], "title": SingleLocaleTextField().deserialize(title)}

    def dump_license(self, obj: dict[str, Any]) -> Any:
        """Dump the license from the vocabulary, or the free-text one."""
        if obj.get("id"):
            return LICENSES.serialize("license", {"license": {"id": obj["id"]}})
        return {"iri": obj.get("link"), "label": SingleLocaleTextField().serialize("title", obj)}

    @post_load
    def merge_license(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Merge the loaded license (id, or title and link) into the rights item."""
        license_ = data.pop("license")
        if "id" in license_:
            # RDM accepts either a vocabulary id or free text (title/description/link), not both -
            # the ccmm description is dropped for a license from the vocabulary
            data.pop("description", None)
        return {**license_, **data}

    @post_dump(pass_original=True)
    def drop_license_description(self, data: dict[str, Any], original: dict[str, Any], **_kwargs: Any) -> Any:
        """Do not dump the description of a vocabulary license, it describes the license, not the terms of use."""
        if original.get("id"):
            data.pop("description", None)
        return data

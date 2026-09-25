#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Marshmallow fields converting between Invenio vocabulary references and CCMM IRIs."""

from __future__ import annotations

from typing import Any, cast, override

import pycountry
from invenio_access.permissions import system_identity
from invenio_base import invenio_url_for
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import ValidationError
from marshmallow.fields import Field


def filtered_mapping(mappings: list[dict[str, Any]], relation: str) -> dict[str, Any] | None:
    """Return the first SKOS mapping with the given relation, or None."""
    return next((mapping for mapping in mappings if mapping["relation"] == relation), None)


class CCMMVocabularyField(Field):
    """Field for serializing CCMM vocabulary values.

    Invenio vocabulary field looks like:

    ```
    {
        "id": "blah",
    }
    ```

    CCMM vocabulary field looks like:

    ```
    {
        "iri": "https://...../blah",
        "label": [
            {
                "lang": "cs",
                "$": "title in cs",
            },
        ],
    }
    ```

    The label is serialized from the vocabulary title and ignored on deserialization.

    The iri is looked up in the SKOS mappings of the vocabulary (case-sensitive). With id_prefix,
    an iri not found there, but starting with id_prefix, is looked up by id - the rest of the iri
    lower-cased (vocabulary ids are lower case, e.g. ".../file-type/TAR" -> "tar").
    """

    def __init__(self, vocab_name: str, id_prefix: str | None = None, **kwargs: Any):
        """Initialize the field with the vocabulary name."""
        self.vocab_type = vocab_name
        self.id_prefix = id_prefix
        super().__init__(**kwargs)

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if value is None:
            return None
        # invenio vocabularies are addressed by (type, id) tuple, the type hint says str
        vocab = vocab_service.read(
            system_identity,
            (self.vocab_type, value["id"]),  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
        )
        mappings = cast("list[dict[str, Any]]", vocab.data.get("mappings", []))
        # relations usable for export, see oarepo_vocabularies.services.schema.SKOSMappingSchema.relation
        mapping = filtered_mapping(mappings, "exactMatch") or filtered_mapping(mappings, "broadMatch")
        if mapping:
            ret: dict[str, Any] = {"iri": mapping["identifier"]}
        else:
            ret = {
                "iri": invenio_url_for(
                    "oarepo_vocabularies_ui.record_detail",
                    type=self.vocab_type,
                    pid_value=vocab["id"],
                )
            }
        # label with xml:lang, in the generic json format of ccmm_invenio.resources.serializers.ccmm.converter
        if title := vocab.data.get("title"):
            ret["label"] = [{"lang": lang, "$": text} for lang, text in title.items()]
        return ret

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if value is None:
            return None
        iri: str | None
        if isinstance(value, str):
            iri = value
        elif isinstance(value, dict):
            iri = value.get("iri")
        else:
            raise ValidationError(f"Invalid value type: {type(value)}")
        if not iri:
            raise ValidationError("Missing vocabulary iri")
        # relations usable for import, see oarepo_vocabularies.services.schema.SKOSMappingSchema.relation
        for relation in ("exactMatch", "narrowMatch"):
            for hit in vocab_service.scan(
                system_identity,
                params={
                    "type": self.vocab_type,
                    "skos": [f"{relation}:{iri}"],  # list, the param interpreter iterates it
                },
                type=self.vocab_type,
            ):
                return {"id": hit["id"]}
        if self.id_prefix and iri.startswith(self.id_prefix):
            item_id = iri.removeprefix(self.id_prefix).lower()
            try:
                vocab_service.read(system_identity, (self.vocab_type, item_id))  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
            except PIDDoesNotExistError:
                pass
            else:
                return {"id": item_id}
        raise ValidationError(f"Could not find vocabulary for {iri}")


class XMLLangField(Field):
    """xml:lang (BCP 47 language tag) <-> invenio languages vocabulary item.

    Invenio languages vocabulary ids are lower-case ISO 639-3 codes ("ces"), xml:lang
    uses the shortest ISO 639 code ("cs", or "ces" when there is no two-letter code).
    Subtags (region, script, ...) are dropped on load.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not value:  # xml:lang="" means "no language"
            return None
        code = str(value).split("-", maxsplit=1)[0].lower()
        language = pycountry.languages.get(**{"alpha_2" if len(code) == 2 else "alpha_3": code})  # noqa: PLR2004
        if language is None:
            raise ValidationError(f"Unknown language: {value}")
        return {"id": language.alpha_3}

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        language = pycountry.languages.get(alpha_3=value["id"])
        if language is None:
            raise ValidationError(f"Unknown language: {value['id']}")
        return getattr(language, "alpha_2", language.alpha_3)

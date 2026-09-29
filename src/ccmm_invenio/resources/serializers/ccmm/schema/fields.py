#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Shared marshmallow fields of the ccmm schemas (language text, locale text, split nesting)."""

from __future__ import annotations

from typing import Any, override

from flask import current_app
from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_dump, pre_load

from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import XMLLangField

NO_LANGUAGE = "und"
"""The language (ISO 639 Undetermined) of a text with an empty xml:lang ("no language")."""


class SplitNested(fields.Nested):
    """List of nested ccmm items, split to one item per value of a repeatable element.

    E.g. a ccmm alternate_title holds all language variants of the title (alternate_title/title
    with xml:lang), while invenio has one additional title per language; a ccmm funding_reference
    has several funders, while invenio has one funding item per funder.

    On load, each ccmm item is copied for every value of its split_on element, the copy holding
    just that value (as a list with a single item). On dump, the nested schema produces one ccmm
    item per invenio item - the items are not grouped back, it is not known which belonged together.

    With unique=True, equal loaded items are kept only once (e.g. a subject from a vocabulary
    loads to the same {"id": ...} for all the language variants of its title).
    """

    def __init__(self, nested: Any, *, split_on: str, unique: bool = False, **kwargs: Any):
        """Create the field, split_on is the name of the repeatable ccmm element."""
        self.split_on = split_on
        self.unique = unique
        super().__init__(nested, many=True, **kwargs)

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, partial: Any = None, **kwargs: Any) -> Any:
        if isinstance(value, list):  # anything else is reported as invalid by Nested
            value = [split_item for item in value for split_item in self._split(item)]
        loaded = super()._deserialize(value, attr, data, partial=partial, **kwargs)
        if not self.unique:
            return loaded
        return [item for idx, item in enumerate(loaded) if item not in loaded[:idx]]

    def _split(self, item: Any) -> list[Any]:
        """Return a copy of the item for each value of the split_on element."""
        if not isinstance(item, dict) or not item.get(self.split_on):
            return [item]  # invalid or missing - left for the nested schema to report
        return [{**item, self.split_on: [value]} for value in item[self.split_on]]


class LanguageTextMixin:
    """Maps a ccmm text element with xml:lang to two invenio fields: the text and lang.

    ccmm: {"<ccmm_element>": {"lang": "cs", "$": "text"}} (or a list with a single such item)
    invenio: {"<text_field>": "text", "lang": {"id": "ces"}}

    The schema declares the text_field field, the lang field is declared here.
    """

    # xml:lang of the ccmm text element, required by the xsd (may be empty)
    lang = XMLLangField()

    ccmm_element: str
    """Name of the ccmm element with the text and xml:lang."""

    text_field: str
    """Name of the invenio field with the text."""

    ccmm_element_many: bool = False
    """The ccmm element is repeatable (a list in generic json), here with a single item (see SplitNested)."""

    @pre_load
    def unpack_language_text(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Split the ccmm text element with xml:lang to the text and lang fields."""
        data = dict(data)
        text = data.pop(self.ccmm_element, None) or {}
        if self.ccmm_element_many:
            if len(text) > 1:
                raise ValidationError(f"Expected a single language variant of {self.ccmm_element}, use SplitNested")
            text = text[0] if text else {}
        # keys only when present, so that a missing text is reported as missing
        data.update(
            {key: text[ccmm_key] for key, ccmm_key in ((self.text_field, "$"), ("lang", "lang")) if ccmm_key in text}
        )
        return data

    @post_dump
    def pack_language_text(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Join the text and lang fields back to the ccmm text element with xml:lang."""
        # xml:lang is required on the ccmm text elements, "" means "no language"
        text = {"lang": data.pop("lang", None) or "", "$": data.pop(self.text_field)}
        data[self.ccmm_element] = [text] if self.ccmm_element_many else text
        return data


class TextWithoutLangField(fields.Field):
    """ccmm text element with xml:lang <-> invenio plain string, the language is dropped.

    On dump, xml:lang is "" ("no language"), the language of the text is not known.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, dict) or "$" not in value:
            raise ValidationError("Expected a text with xml:lang")
        return value["$"]

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        return None if value is None else {"lang": "", "$": value}


class SingleItemListNested(fields.Nested):
    """A single nested ccmm item <-> invenio list with this one item."""

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, partial: Any = None, **kwargs: Any) -> Any:
        return [super()._deserialize(value, attr, data, partial=partial, **kwargs)]

    @override
    def _serialize(self, nested_obj: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        # ponytail: ccmm has a single item - further invenio items are dropped on dump
        return super()._serialize(nested_obj[0] if nested_obj else None, attr, obj, **kwargs)


class SingleLocaleTextField(fields.Field):
    """ccmm multilingual text (a list of {"lang", "$"}) <-> RDM i18n dict with a single locale.

    RDM free-text rights (title, description) accept just one of the configured invenio locales:
    the variant in the default locale (BABEL_DEFAULT_LOCALE) is used, otherwise the first one in
    a configured locale, otherwise the first one (reported by invenio) - the other variants are dropped.
    A variant without a language is taken as the default locale.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, list) or not value:
            raise ValidationError("Expected a list of texts with xml:lang")
        default_locale = current_app.config.get("BABEL_DEFAULT_LOCALE", "en")
        # the same locales RDM validates against (invenio_rdm_records...metadata.locale_validation)
        locales = [default_locale] + [
            locale.language for locale in current_app.extensions["invenio-i18n"].get_locales()
        ]
        variants = {(variant.get("lang") or default_locale).split("-")[0]: variant.get("$") for variant in value}
        locale = next((locale for locale in locales if locale in variants), next(iter(variants)))
        return {locale: variants[locale]}

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        return [{"lang": locale, "$": text} for locale, text in value.items()] if value else None


class MultilingualField(fields.Field):
    """ccmm text with language variants (a list of {"lang", "$"}) <-> model multilingual.

    The model multilingual is a list of {"lang": {"id": "ces"}, "value": "text"}, the language
    is required there - a text with an empty xml:lang ("no language") has the und (Undetermined)
    language, dumped back as an empty xml:lang.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ValidationError("Expected a list of language variants")
        return [
            {"lang": XMLLangField().deserialize(item.get("lang")) or {"id": NO_LANGUAGE}, "value": item.get("$")}
            for item in value
        ]

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        return [
            {
                "lang": "" if item["lang"]["id"] == NO_LANGUAGE else XMLLangField().serialize("lang", item),
                "$": item["value"],
            }
            for item in value
        ]


class IriLabelSchema(Schema):
    """ccmm entity with an iri and a multilingual label (file, documentation)."""

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 1..1
    iri = fields.String(required=True)

    # ccmm 0..n
    label = MultilingualField()


class ApplicationProfileSchema(IriLabelSchema):
    """ccmm application profile.

    The iri is 1..1 in ccmm, but optional in the model (the label is required there),
    an empty <iri/> is taken as a missing one.
    """

    iri = fields.String()

    @pre_load
    def drop_empty_iri(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Drop an empty <iri/>, it is not an iri."""
        return {k: v for k, v in data.items() if k != "iri" or v}

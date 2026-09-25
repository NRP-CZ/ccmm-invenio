#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import ValidationError

from ccmm_invenio.resources.serializers.ccmm.converter import convert_xml_to_json
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import AlternateTitleSchema, DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import XMLLangField

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLE = (
    Path(__file__).parent.parent
    / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml/ccmm_sample.xml"
)
TRANSLATED_TITLE = "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/TranslatedTitle"


@pytest.fixture(scope="module")
def title_types(app, database, search):
    vocab_service.create_type(system_identity, "titletypes", "ttyp")
    for entry in yaml.safe_load((FIXTURES / "titletypes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "titletypes", **entry})
    vocab_service.indexer.refresh()


@pytest.mark.parametrize(
    ("xml_lang", "vocabulary_item"),
    [("cs", {"id": "ces"}), ("ces", {"id": "ces"}), ("en-GB", {"id": "eng"}), ("", None)],
)
def test_xml_lang_load(xml_lang, vocabulary_item):
    assert XMLLangField().deserialize(xml_lang) == vocabulary_item


def test_xml_lang_dump():
    # the shortest code, three-letter only when there is no two-letter one
    assert XMLLangField().serialize("lang", {"lang": {"id": "ces"}}) == "cs"
    assert XMLLangField().serialize("lang", {"lang": {"id": "haw"}}) == "haw"
    with pytest.raises(ValidationError):
        XMLLangField().deserialize("xx")


def test_load_from_ccmm_sample(title_types):
    data, errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    assert errors == []

    loaded = DatasetMetadataSchema(only=("additional_titles",)).load(data)

    assert loaded == {
        "additional_titles": [
            {
                "title": "Air quality measurements in Central Bohemian Region in 2024.",
                "lang": {"id": "eng"},
                "type": {"id": "translated-title"},
            }
        ]
    }


def test_one_title_per_language(title_types):
    ccmm = {
        "alternate_title": [
            {
                "iri": "https://example.org/alternate-title",
                "title": [{"lang": "cs", "$": "Přeložený název"}, {"lang": "en", "$": "Translated title"}],
                "alternate_title_type": {"iri": TRANSLATED_TITLE},
            }
        ]
    }
    loaded = DatasetMetadataSchema(only=("additional_titles",)).load(ccmm)["additional_titles"]
    assert [(title["title"], title["lang"]) for title in loaded] == [
        ("Přeložený název", {"id": "ces"}),
        ("Translated title", {"id": "eng"}),
    ]

    # a missing type is "other"
    assert DatasetMetadataSchema(only=("additional_titles",)).load(
        {"alternate_title": [{"title": [{"lang": "en", "$": "Untyped title"}]}]}
    )["additional_titles"] == [{"title": "Untyped title", "lang": {"id": "eng"}, "type": {"id": "other"}}]

    # an alternate title without a title is reported, not dropped
    with pytest.raises(ValidationError) as excinfo:
        DatasetMetadataSchema(only=("additional_titles",)).load(
            {"alternate_title": [{"alternate_title_type": {"iri": TRANSLATED_TITLE}}]}
        )
    assert excinfo.value.messages == {"alternate_title": {0: {"title": ["Missing data for required field."]}}}

    # dump: one ccmm alternate title per invenio additional title, the type gets its label
    dumped = AlternateTitleSchema().dump(loaded[0])
    assert dumped["title"] == [{"lang": "cs", "$": "Přeložený název"}]
    assert dumped["alternate_title_type"]["iri"] == TRANSLATED_TITLE

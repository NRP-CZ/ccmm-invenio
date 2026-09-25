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
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema, DescriptionSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLE = (
    Path(__file__).parent.parent
    / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml/ccmm_sample.xml"
)
ABSTRACT = "https://vocabs.ccmm.cz/registry/codelist/DescriptionType/Abstract"


@pytest.fixture(scope="module")
def description_types(app, database, search):
    vocab_service.create_type(system_identity, "descriptiontypes", "dsctyp")
    for entry in yaml.safe_load((FIXTURES / "descriptiontypes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "descriptiontypes", **entry})
    vocab_service.indexer.refresh()


def test_load_from_ccmm_sample(description_types):
    data, errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    assert errors == []

    loaded = DatasetMetadataSchema(only=("additional_descriptions",)).load(data)

    assert loaded == {
        "additional_descriptions": [
            {
                "description": "Tato datová sada obsahuje měření kvality ovzduší ve středních Čechách v\n"
                "            roce 2024.",
                "lang": {"id": "ces"},
                "type": {"id": "abstract"},
            }
        ]
    }


def test_load_and_dump(description_types):
    schema = DescriptionSchema()

    # a missing type is "other"
    assert schema.load({"description_text": {"lang": "en", "$": "Untyped description"}}) == {
        "description": "Untyped description",
        "lang": {"id": "eng"},
        "type": {"id": "other"},
    }

    # a missing description is reported as missing
    with pytest.raises(ValidationError) as excinfo:
        schema.load({"description_type": {"iri": ABSTRACT}})
    assert excinfo.value.messages == {"description": ["Missing data for required field."]}

    # dump back to ccmm, the type gets its iri and label
    dumped = schema.dump({"description": "Popis", "lang": {"id": "ces"}, "type": {"id": "abstract"}})
    assert dumped["description_text"] == {"lang": "cs", "$": "Popis"}
    assert dumped["description_type"]["iri"] == ABSTRACT
    assert "description" not in dumped


def test_dump_main_description_as_other(description_types):
    """The main RDM description is exported as the first ccmm description, of type "other"."""
    dumped = DatasetMetadataSchema().dump(
        {
            "title": "A dataset",
            "description": "The main description of the dataset.",
            "additional_descriptions": [{"description": "An additional one.", "type": {"id": "abstract"}}],
        }
    )
    descriptions = dumped["description"]
    assert len(descriptions) == 2
    # the main description goes first, with type "other"
    assert descriptions[0]["description_text"] == {"lang": "", "$": "The main description of the dataset."}
    assert (
        descriptions[0]["description_type"]["iri"] == "https://vocabs.ccmm.cz/registry/codelist/DescriptionType/Other"
    )
    # ... then the additional ones
    assert descriptions[1]["description_type"]["iri"] == ABSTRACT


def test_dump_no_main_description(description_types):
    """Without the main RDM description (a record imported from ccmm), nothing is added."""
    dumped = DatasetMetadataSchema().dump({"title": "A dataset"})
    assert "description" not in dumped

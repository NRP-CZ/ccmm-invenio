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
from invenio_rdm_records.services.schemas.metadata import record_identifiers_schemes
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow_utils.schemas import IdentifierSchema as RDMIdentifierSchema

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.identifiers import IdentifierSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)


@pytest.fixture(scope="module")
def identifier_schemes(app, database, search):
    vocab_service.create_type(system_identity, "identifierschemes", "idsch")
    for entry in yaml.safe_load((FIXTURES / "identifierschemes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "identifierschemes", **entry})
    vocab_service.indexer.refresh()


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_load_samples(identifier_schemes, sample):
    data, errors = convert_xml_to_json(sample.read_text(encoding="utf-8"))
    assert errors == []

    loaded = DatasetMetadataSchema(only=("identifiers",)).load(data)

    assert len(loaded["identifiers"]) == len(data["identifier"])
    # valid RDM record identifiers
    assert (
        RDMIdentifierSchema(allowed_schemes=record_identifiers_schemes, many=True).validate(loaded["identifiers"]) == {}
    )


def test_ccmm_sample(identifier_schemes):
    data, _ = convert_xml_to_json((SAMPLES_DIR / "ccmm_sample.xml").read_text(encoding="utf-8"))
    assert DatasetMetadataSchema(only=("identifiers",)).load(data)["identifiers"] == [
        {"identifier": "10.45321/as36sl", "scheme": "doi"},
        # a local scheme, not in the vocabulary - the iri is used as an url
        {"identifier": "https://organization.cz/datasets/air-q-cb-25-23", "scheme": "url"},
    ]


def test_dataset_iri(identifier_schemes):
    # the dataset iri is kept as the iri, it is not added to the identifiers
    ccmm = {"iri": "https://organization.cz/dataset_server/dataset_id", "identifier": []}
    loaded = DatasetMetadataSchema(only=("iri", "identifiers")).load(ccmm)
    assert loaded == {"iri": "https://organization.cz/dataset_server/dataset_id", "identifiers": []}
    assert DatasetMetadataSchema(only=("iri",)).dump(loaded) == {
        "iri": "https://organization.cz/dataset_server/dataset_id"
    }


@pytest.mark.parametrize(
    ("iri", "identifier"),
    [
        ("https://doi.org/10.2342/234234", {"identifier": "10.2342/234234", "scheme": "doi"}),
        ("https://hdl.handle.net/20.500.12345/1", {"identifier": "20.500.12345/1", "scheme": "handle"}),
        # no known scheme - the iri is an url
        ("https://example.org/local/123", {"identifier": "https://example.org/local/123", "scheme": "url"}),
    ],
)
def test_unknown_scheme_detected_from_iri(identifier_schemes, iri, identifier):
    ccmm = {"iri": iri, "value": "123", "scheme": {"iri": "https://example.org/unknown-scheme/"}}
    assert IdentifierSchema().load(ccmm) == identifier


def test_unknown_scheme_without_iri(identifier_schemes):
    assert IdentifierSchema().load({"value": "local-123", "scheme": {"iri": "https://example.org/local/"}}) == {
        "identifier": "local-123",
        "scheme": "other",
    }


def test_dump(identifier_schemes):
    dumped = IdentifierSchema().dump({"identifier": "10.45321/as36sl", "scheme": "doi"})
    assert dumped["value"] == "10.45321/as36sl"
    assert dumped["scheme"]["iri"] == "https://doi.org/"
    # the iri is derived from the identifier and scheme
    assert dumped["iri"] == "https://doi.org/10.45321/as36sl"
    # the dumped identifier is a valid ccmm identifier
    _xml, errors = XMLToGenericJSONConverter().json_to_xml(ccmm_1_1_0_schema, dumped, f"{{{NS_CCMM_1_1_0}}}identifier")
    assert errors == []

    # no url for the "other" scheme - no iri
    assert "iri" not in IdentifierSchema().dump({"identifier": "local-123", "scheme": "other"})


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_dump_samples_iri(identifier_schemes, sample):
    data, _ = convert_xml_to_json(sample.read_text(encoding="utf-8"))
    loaded = DatasetMetadataSchema(only=("identifiers",)).load(data)
    dumped = DatasetMetadataSchema(only=("identifiers",)).dump(loaded)
    # the iri of the source identifiers is reconstructed
    assert [identifier["iri"] for identifier in dumped["identifier"]] == [
        identifier["iri"] for identifier in data["identifier"]
    ]

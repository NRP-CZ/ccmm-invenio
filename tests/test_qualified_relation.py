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
from invenio_rdm_records.services.schemas.metadata import ContributorSchema as RDMContributorSchema
from invenio_rdm_records.services.schemas.metadata import CreatorSchema as RDMCreatorSchema
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.proxies import current_service as vocab_service

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.agents import CCMM_ROLE_CREATOR, CCMM_ROLE_PUBLISHER
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
FIELDS = ("creators", "contributors", "publisher")
DATA_MANAGER = "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Contributor/DataManager"
CUNI = "024d6js02"  # Univerzita Karlova, ROR


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    vocab_service.create_type(system_identity, "identifierschemes", "idsch")
    for entry in yaml.safe_load((FIXTURES / "identifierschemes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "identifierschemes", **entry})
    vocab_service.create_type(system_identity, "contributorsroles", "cor")
    for entry in yaml.safe_load((FIXTURES / "resourceagentroletypes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "contributorsroles", **entry})
    vocab_service.indexer.refresh()


@pytest.fixture(scope="module")
def affiliations(app, database, search):
    service = current_service_registry.get("affiliations")
    service.create(
        system_identity,
        {"id": CUNI, "name": "Univerzita Karlova", "identifiers": [{"identifier": CUNI, "scheme": "ror"}]},
    )
    service.indexer.refresh()


def load(sample: str) -> dict:
    data, errors = convert_xml_to_json((SAMPLES_DIR / sample).read_text(encoding="utf-8"))
    assert errors == []
    return DatasetMetadataSchema(only=FIELDS).load(data)


def test_ccmm_sample(vocabularies, affiliations):
    assert load("ccmm_sample.xml") == {
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Novák",
                    "given_name": "Jan",
                    "family_name": "Novák",
                    "identifiers": [{"identifier": "0000-0002-1825-0097", "scheme": "orcid"}],
                },
                # the ROR is in the affiliations vocabulary - it is the id
                "affiliations": [{"id": CUNI, "name": "Univerzita Karlova"}],
            }
        ],
        # a person as the publisher, by name
        "publisher": "Ivan Janouch",
    }


def test_family_name_from_name(vocabularies):
    creators = load("1m3t2-78951.xml")["creators"]
    # "Paldusová, Kateřina" without given_name / family_name in ccmm
    assert creators[0]["person_or_org"]["family_name"] == "Paldusová"
    assert creators[0]["person_or_org"]["given_name"] == "Kateřina"


def test_contributor(vocabularies):
    loaded = DatasetMetadataSchema(only=FIELDS).load(
        {
            "qualified_relation": [
                {"relation": {"organization": {"name": "Data centre"}}, "role": {"iri": DATA_MANAGER}},
                {"relation": {"organization": {"name": "Publisher A"}}, "role": {"iri": CCMM_ROLE_PUBLISHER}},
                {"relation": {"organization": {"name": "Publisher B"}}, "role": {"iri": CCMM_ROLE_PUBLISHER}},
            ]
        }
    )
    assert loaded == {
        "contributors": [
            {"person_or_org": {"type": "organizational", "name": "Data centre"}, "role": {"id": "datamanager"}}
        ],
        "publisher": "Publisher A, Publisher B",
    }
    assert RDMContributorSchema(many=True).validate(loaded["contributors"]) == {}


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_valid_for_rdm(vocabularies, sample):
    loaded = load(sample)
    assert RDMCreatorSchema(many=True).validate(loaded.get("creators", [])) == {}
    assert RDMContributorSchema(many=True).validate(loaded.get("contributors", [])) == {}


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_round_trip(vocabularies, sample):
    loaded = load(sample)
    dumped = DatasetMetadataSchema(only=FIELDS).dump(loaded)["qualified_relation"]

    for relation in dumped:
        _xml, errors = XMLToGenericJSONConverter().json_to_xml(
            ccmm_1_1_0_schema, relation, f"{{{NS_CCMM_1_1_0}}}resource_to_agent_relationship"
        )
        assert errors == [], relation
    assert {relation["role"]["iri"] for relation in dumped} <= {CCMM_ROLE_CREATOR, CCMM_ROLE_PUBLISHER, DATA_MANAGER}
    assert DatasetMetadataSchema(only=FIELDS).load({"qualified_relation": dumped}) == loaded


def test_role_labels_dumped(vocabularies, affiliations):
    """The Creator / Publisher roles are exported with the vocabulary labels."""
    dumped = DatasetMetadataSchema(only=FIELDS).dump(load("ccmm_sample.xml"))["qualified_relation"]
    roles = {relation["role"]["iri"]: relation["role"] for relation in dumped}
    assert roles[CCMM_ROLE_CREATOR]["label"] == [{"lang": "cs", "$": "Autor"}, {"lang": "en", "$": "Creator"}]
    publisher_labels = {label["$"] for label in roles[CCMM_ROLE_PUBLISHER]["label"]}
    assert publisher_labels == {"Vydavatel", "Publisher"}


def test_affiliation_ror_dumped(vocabularies, affiliations):
    dumped = DatasetMetadataSchema(only=FIELDS).dump(load("ccmm_sample.xml"))["qualified_relation"]
    (affiliation,) = dumped[0]["relation"]["person"]["affiliation"]
    assert affiliation["name"] == "Univerzita Karlova"
    assert [identifier["value"] for identifier in affiliation["identifier"]] == [CUNI]

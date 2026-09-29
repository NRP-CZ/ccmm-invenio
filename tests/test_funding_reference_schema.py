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
from invenio_rdm_records.services.schemas.metadata import FundingSchema as RDMFundingSchema
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.proxies import current_service as vocab_service

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
GACR = "01pv73b02"  # Grantová agentura České republiky, in the funders vocabulary
MSMT = "037n8p820"  # Ministerstvo školství, mládeže a tělovýchovy, not in the funders vocabulary


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    vocab_service.create_type(system_identity, "identifierschemes", "idsch")
    for entry in yaml.safe_load((FIXTURES / "identifierschemes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "identifierschemes", **entry})
    vocab_service.indexer.refresh()

    funders = current_service_registry.get("funders")
    funders.create(
        system_identity,
        {
            "id": GACR,
            "name": "Grantová agentura České republiky",
            "identifiers": [{"identifier": GACR, "scheme": "ror"}],
        },
    )
    funders.indexer.refresh()


def load_funding(sample: str) -> list:
    data, errors = convert_xml_to_json((SAMPLES_DIR / sample).read_text(encoding="utf-8"))
    assert errors == []
    return DatasetMetadataSchema(only=("funding",)).load(data)["funding"]


def test_ccmm_sample(vocabularies):
    assert load_funding("ccmm_sample.xml") == [
        {
            "funder": {
                "id": GACR,  # in the funders vocabulary
                "name": "Grantová agentura České republiky",
            },
            "award": {
                "number": "https://doi.org/award-identifier",
                "title": {"en": "Program for air pollution research"},
                "identifiers": [{"identifier": "https://funder-org.org/grants/123456789", "scheme": "url"}],
                "program": "https://funder-org.org/program/abcdefgh",
            },
        }
    ]


def test_funder_not_in_vocabulary(vocabularies):
    (funding,) = load_funding("dmq82-ed856.xml")
    # not in the funders vocabulary - no id, by name (RDM funder has no identifiers)
    assert funding["funder"] == {"name": "Ministerstvo školství, mládeže a tělovýchovy"}
    assert funding["award"] == {
        "number": "EH23_021/0008433",
        "title": {"en": "Development of special wire semiproducts for welding and 3D printing"},
        "program": "Operační program Jan Amos Komenský",
    }


@pytest.mark.parametrize("sample", ["ccmm_sample.xml", "dmq82-ed856.xml"])
def test_funding_is_valid_for_rdm(vocabularies, sample):
    for funding in load_funding(sample):
        assert RDMFundingSchema().validate(funding) == {}


def test_one_funding_per_funder(vocabularies):
    ccmm = {
        "funding_reference": [
            {
                "local_identifier": "123",
                "funder": [
                    {"organization": {"name": "Funder A"}},
                    {"person": {"name": "Jan Novák"}},  # a person funder, by name
                ],
            }
        ]
    }
    assert DatasetMetadataSchema(only=("funding",)).load(ccmm)["funding"] == [
        {"funder": {"name": "Funder A"}, "award": {"number": "123"}},
        {"funder": {"name": "Jan Novák"}, "award": {"number": "123"}},
    ]


@pytest.mark.parametrize("sample", ["ccmm_sample.xml", "dmq82-ed856.xml"])
def test_dump(vocabularies, sample):
    funding = load_funding(sample)
    dumped = DatasetMetadataSchema(only=("funding",)).dump({"funding": funding})["funding_reference"]

    for funding_reference in dumped:
        _xml, errors = XMLToGenericJSONConverter().json_to_xml(
            ccmm_1_1_0_schema, funding_reference, f"{{{NS_CCMM_1_1_0}}}funding_reference"
        )
        assert errors == []

    # loading the dumped funding references gives the same funding
    assert DatasetMetadataSchema(only=("funding",)).load({"funding_reference": dumped})["funding"] == funding

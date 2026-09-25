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
from invenio_rdm_records.services.schemas.metadata import RightsSchema
from invenio_vocabularies.proxies import current_service as vocab_service

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.terms_of_use import TermsOfUseSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
UNKNOWN_LICENSE = "https://example.org/licenses/local-license"


@pytest.fixture(scope="module")
def licenses(app, database, search):
    vocab_service.create_type(system_identity, "licenses", "lic")
    for entry in yaml.safe_load((FIXTURES / "licenses.yaml").read_text(encoding="utf-8")):
        if entry["id"] in ("cc-by-4.0", "cc0-1.0"):
            entry.pop("hierarchy", None)  # parents are not loaded here
            vocab_service.create(system_identity, {"type": "licenses", **entry})
    vocab_service.indexer.refresh()


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_load_samples(licenses, sample):
    data, errors = convert_xml_to_json(sample.read_text(encoding="utf-8"))
    assert errors == []

    rights = DatasetMetadataSchema(only=("rights",)).load(data)["rights"]

    assert len(rights) == 1
    assert rights[0]["id"] == "cc-by-4.0"
    assert RightsSchema(many=True).validate(rights) == {}


def test_ccmm_sample(licenses):
    data, _ = convert_xml_to_json((SAMPLES_DIR / "ccmm_sample.xml").read_text(encoding="utf-8"))
    # the terms of use description is dropped - RDM does not accept it together with a vocabulary id
    assert DatasetMetadataSchema(only=("rights",)).load(data)["rights"] == [{"id": "cc-by-4.0"}]


def test_license_not_in_vocabulary(licenses):
    loaded = TermsOfUseSchema().load(
        {
            "access_rights": {"iri": "http://purl.org/coar/access_right/c_abf2"},
            "license": {
                "iri": UNKNOWN_LICENSE,
                "label": [{"lang": "cs", "$": "Místní licence"}, {"lang": "en", "$": "Local license"}],
            },
        }
    )
    # free-text license, a single locale (the default one) as RDM requires
    assert loaded == {"link": UNKNOWN_LICENSE, "title": {"en": "Local license"}}
    assert RightsSchema().validate(loaded) == {}

    # a free-text license keeps the description
    with_description = TermsOfUseSchema().load(
        {"license": {"iri": UNKNOWN_LICENSE}, "description": [{"lang": "cs", "$": "Popis podmínek"}]}
    )
    assert with_description["description"] == {"cs": "Popis podmínek"}
    assert RightsSchema().validate(with_description) == {}
    assert TermsOfUseSchema().dump(with_description)["description"] == [{"lang": "cs", "$": "Popis podmínek"}]

    # without a label, the iri is the title
    assert TermsOfUseSchema().load({"license": {"iri": UNKNOWN_LICENSE}})["title"] == {"en": UNKNOWN_LICENSE}


def test_dump(licenses):
    dumped = DatasetMetadataSchema(only=("rights",)).dump(
        {
            "rights": [
                {"id": "cc-by-4.0", "description": {"en": "Use with care"}},
                {"id": "cc0-1.0"},  # ccmm has a single license - dropped
            ]
        }
    )["terms_of_use"]
    assert dumped["license"]["iri"] == CC_BY
    assert {"lang": "en", "$": "Creative Commons Attribution 4.0 International"} in dumped["license"]["label"]
    # the description of a vocabulary license describes the license, not the terms of use
    assert "description" not in dumped

    # access_rights is not mapped (see TermsOfUseSchema), it is the only thing missing for a valid ccmm element
    _xml, errors = XMLToGenericJSONConverter().json_to_xml(
        ccmm_1_1_0_schema, dumped, f"{{{NS_CCMM_1_1_0}}}terms_of_use"
    )
    assert len(errors) == 1
    assert "access_rights" in errors[0].reason

    # free-text license
    assert TermsOfUseSchema().dump({"link": UNKNOWN_LICENSE, "title": {"en": "Local license"}})["license"] == {
        "iri": UNKNOWN_LICENSE,
        "label": [{"lang": "en", "$": "Local license"}],
    }

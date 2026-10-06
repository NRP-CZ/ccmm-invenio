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
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.contrib.subjects.schema import SubjectRelationSchema
from invenio_vocabularies.records.models import VocabularyScheme

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.subjects import SubjectSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
FORD = "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/"
INSPIRE = "http://inspire.ec.europa.eu/theme"
USED_SUBJECTS = {"ford:10509", "ford:10601", "ford:10606", "ford:30102", "ford:30304", "ford:20501", "inspire:ef"}


@pytest.fixture(scope="module")
def subjects(app, database, search):
    # the schemes as in fixtures/vocabularies.yaml
    VocabularyScheme.create(id="FORD", parent_id="subjects", name="OECD FORD Subject Category (Frascati)", uri=FORD)
    VocabularyScheme.create(id="INSPIRE", parent_id="subjects", name="INSPIRE theme register", uri=INSPIRE)
    service = current_service_registry.get("subjects")
    for data_file in ("subjects.yaml", "subjects_inspire.yaml"):
        for entry in yaml.safe_load((FIXTURES / data_file).read_text(encoding="utf-8")):
            if entry["id"] in USED_SUBJECTS:
                service.create(system_identity, entry)
    service.indexer.refresh()


def load_subjects(sample: str) -> list:
    data, errors = convert_xml_to_json((SAMPLES_DIR / sample).read_text(encoding="utf-8"))
    assert errors == []
    return DatasetMetadataSchema(only=("subjects",)).load(data)["subjects"]


def test_ccmm_sample(subjects):
    assert load_subjects("ccmm_sample.xml") == [
        # in the vocabulary - one subject for both language variants of the title
        {"id": "ford:10509"},
        # keywords
        {"subject": "kvalita ovzduší"},
        # an INSPIRE theme, in the vocabulary as well
        {"id": "inspire:ef"},
    ]


def test_keywords_per_language(subjects):
    assert load_subjects("1m3t2-78951.xml") == [
        {"id": "ford:10601"},
        {"id": "ford:10606"},
        {"id": "ford:30102"},
        # one keyword per language variant
        {"subject": "lidské neutrofily"},
        {"subject": "human neutrophils"},
        {"subject": "NETy"},
        {"subject": "NETs"},
        {"subject": "NETóza"},
        {"subject": "NETosis"},
        {"subject": "mikroskopie"},
        {"subject": "microscopy"},
    ]


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_valid_for_rdm(subjects, sample):
    assert SubjectRelationSchema(many=True).validate(load_subjects(sample)) == {}


def test_dump(subjects):
    dumped = SubjectSchema().dump({"id": "ford:10509"})
    # iri, title, classification code and scheme (with its name) from the vocabulary
    assert dumped == {
        "iri": f"{FORD}10000/10500/10509",
        "title": [
            {"lang": "cs", "$": "Meteorologie, vědy o atmosféře"},
            {"lang": "en", "$": "Meteorology and atmospheric sciences"},
        ],
        "classification_code": "10509",
        "subject_scheme": {"iri": FORD, "label": [{"lang": "en", "$": "OECD FORD Subject Category (Frascati)"}]},
    }
    assert SubjectSchema().dump({"id": "inspire:ef"}) == {
        "iri": f"{INSPIRE}/ef",
        "title": [
            {"lang": "cs", "$": "Zařízení pro sledování životního prostředí"},
            {"lang": "en", "$": "Environmental monitoring facilities"},
        ],
        "classification_code": "EF",
        "subject_scheme": {"iri": INSPIRE, "label": [{"lang": "en", "$": "INSPIRE theme register"}]},
    }
    # the language of a keyword is not known
    assert SubjectSchema().dump({"subject": "kvalita ovzduší"}) == {"title": [{"lang": "", "$": "kvalita ovzduší"}]}


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_round_trip(subjects, sample):
    loaded = load_subjects(sample)
    dumped = DatasetMetadataSchema(only=("subjects",)).dump({"subjects": loaded})["subject"]

    for subject in dumped:
        _xml, errors = XMLToGenericJSONConverter().json_to_xml(
            ccmm_1_1_0_schema, subject, f"{{{NS_CCMM_1_1_0}}}subject"
        )
        assert errors == []

    assert DatasetMetadataSchema(only=("subjects",)).load({"subject": dumped})["subjects"] == loaded


def test_classification_code_from_id(subjects):
    # without the classification_code prop, the code is the id without the scheme prefix
    service = current_service_registry.get("subjects")
    service.create(
        system_identity,
        {"id": "ford:99999", "scheme": "FORD", "subject": "Without a code", "title": {"en": "Without a code"}},
    )
    service.indexer.refresh()
    assert SubjectSchema().dump({"id": "ford:99999"})["classification_code"] == "99999"

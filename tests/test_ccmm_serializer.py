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

from ccmm_invenio.resources.serializers import CCMMXMLSerializer
from ccmm_invenio.resources.serializers.ccmm.converter import convert_xml_to_json
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
DATA_MANAGER = "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Contributor/DataManager"
SAMPLE = (
    Path(__file__).parent.parent
    / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml/dataset-mini.xml"
)


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    for vocabulary_type, pid_type, data_file in (
        ("identifierschemes", "idsch", "identifierschemes"),
        ("datetypes", "dtt", "datetypes"),
        ("licenses", "lic", "licenses"),
        ("resourcetypes", "rsrct", "resourcetypes"),  # a dataset without a resource type gets "dataset"
        ("accessrights", "v-ar", "accessrights"),
        ("contributorsroles", "cor", "resourceagentroletypes"),  # the data manager of the metadata record
    ):
        vocab_service.create_type(system_identity, vocabulary_type, pid_type)
        for entry in yaml.safe_load((FIXTURES / f"{data_file}.yaml").read_text(encoding="utf-8")):
            vocab_service.create(system_identity, {"type": vocabulary_type, **entry})
    vocab_service.indexer.refresh()


def test_export_is_valid_ccmm_xml(app, vocabularies, monkeypatch):
    monkeypatch.setitem(app.config, "THEME_SITENAME", "Test repository")
    # import of the minimal sample ...
    data, errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    assert errors == []
    record = DatasetSchema().load(data)
    assert record["ccmm_xml"] == data["ccmm_xml"]
    # a Created time reference becomes the RDM publication date
    assert record["metadata"]["publication_date"] == "2024-05-01"

    # the metadata record of the source is stored, its data manager (the DataCite unknown placeholder
    # in the sample) is an RDM contributor there - and not among the contributors of the dataset
    (stored,) = record["metadata"]["metadata_identifications"]
    assert stored["qualified_relations"] == [
        {
            "person_or_org": {"type": "personal", "name": ":unkn", "given_name": ":unkn", "family_name": ":unkn"},
            "role": {"id": "datamanager"},
        }
    ]
    assert "contributors" not in record["metadata"]

    # the sample is embargoed without an "Available" date - the end of the embargo is not known,
    # the files are restricted
    assert record["access"] == {"record": "public", "files": "restricted"}

    # ... and export back to a valid ccmm xml document
    record.update({"created": "2026-09-01T10:00:00+00:00", "updated": "2026-09-24T12:00:00+00:00"})
    xml = CCMMXMLSerializer().serialize_object(record)
    exported, errors = convert_xml_to_json(xml)
    assert errors == []
    # the stored metadata record is exported without changes (not made from the technical metadata)
    (metadata_record,) = exported["metadata_identification"]
    (source_metadata_record,) = data["metadata_identification"]
    assert metadata_record["original_repository"] == source_metadata_record["original_repository"]
    assert metadata_record["conforms_to_standard"] == source_metadata_record["conforms_to_standard"]
    assert "date_created" not in metadata_record
    assert "iri" not in metadata_record
    (data_manager,) = metadata_record["qualified_relation"]
    assert data_manager["role"]["iri"] == DATA_MANAGER
    assert data_manager["relation"]["person"]["name"] == ":unkn"
    assert DATA_MANAGER not in [relation["role"]["iri"] for relation in exported["qualified_relation"]]
    assert exported["terms_of_use"]["access_rights"]["iri"] == "http://purl.org/coar/access_right/c_16ec"
    assert exported["identifier"][0]["value"] == "10.48700/datst.xd12h-dfz24"
    assert str(exported["publication_year"]) == "2024"


def created_here(record: dict) -> dict:
    """Make an imported record look like one created here - no source xml, no stored metadata record."""
    del record["ccmm_xml"]
    del record["metadata"]["metadata_identifications"]
    record.update(
        {
            "created": "2026-09-01T10:00:00+00:00",
            "updated": "2026-09-24T12:00:00+00:00",
            "links": {"self": "https://127.0.0.1:5000/api/ccmm-dataset/abcde-12345"},
        }
    )
    return record


def test_metadata_record_of_record_created_here(app, vocabularies, monkeypatch):
    monkeypatch.setitem(app.config, "THEME_SITENAME", "Test repository")
    data, _errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    record = created_here(DatasetSchema().load(data))
    exported, errors = convert_xml_to_json(CCMMXMLSerializer().serialize_object(record))
    assert errors == []
    # made from the technical metadata of the record
    (metadata_record,) = exported["metadata_identification"]
    assert metadata_record["iri"] == "https://127.0.0.1:5000/api/ccmm-dataset/abcde-12345"
    assert metadata_record["date_created"] == "2026-09-01"
    assert metadata_record["date_updated"] == ["2026-09-24"]
    assert metadata_record["conforms_to_standard"][0]["iri"] == "https://schema.ccmm.cz/research-data/1.1.0"
    assert metadata_record["original_repository"] == {
        "iri": app.config["SITE_UI_URL"],
        "label": [{"lang": "en", "$": "Test repository"}],
    }
    # without data manager contributors, this repository is the data manager
    (data_manager,) = metadata_record["qualified_relation"]
    assert data_manager["role"]["iri"] == DATA_MANAGER
    assert data_manager["relation"]["organization"]["name"] == "Test repository"


def test_data_manager_contributor_in_generated_metadata_record(app, vocabularies):
    data, _errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    record = created_here(DatasetSchema().load(data))
    record["metadata"]["contributors"] = [
        {"person_or_org": {"type": "organizational", "name": "Data centre"}, "role": {"id": "datamanager"}}
    ]
    exported, errors = convert_xml_to_json(CCMMXMLSerializer().serialize_object(record))
    assert errors == []
    # the data manager contributor is copied into the metadata record ...
    (metadata_record,) = exported["metadata_identification"]
    (data_manager,) = metadata_record["qualified_relation"]
    assert data_manager["relation"]["organization"]["name"] == "Data centre"
    # ... and stays a contributor of the dataset
    assert [
        relation["relation"]["organization"]["name"]
        for relation in exported["qualified_relation"]
        if relation["role"]["iri"] == DATA_MANAGER
    ] == ["Data centre"]


def test_dataset_iri(vocabularies):
    data, _errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))
    data["iri"] = "https://organization.cz/dataset_server/dataset_id"
    record = DatasetSchema().load(data)
    # the dataset iri is kept as the iri, not added to the identifiers
    assert record["metadata"]["iri"] == "https://organization.cz/dataset_server/dataset_id"
    assert "https://organization.cz/dataset_server/dataset_id" not in str(record["metadata"]["identifiers"])
    exported, errors = convert_xml_to_json(CCMMXMLSerializer().serialize_object(record))
    assert errors == []
    assert exported["iri"] == "https://organization.cz/dataset_server/dataset_id"

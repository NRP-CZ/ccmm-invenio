#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Import a CCMM XML record over the REST API."""

from __future__ import annotations

from pathlib import Path

import pytest
from invenio_access.permissions import system_identity
from invenio_rdm_records.fixtures.vocabularies import VocabulariesFixture
from invenio_records_resources.proxies import current_service_registry
from invenio_search.proxies import current_search

from ccmm_invenio.resources.serializers.ccmm.converter import CCMM_XML_MIMETYPE, convert_xml_to_json
from tests.model import ccmm_dataset

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
SAMPLE = SAMPLES_DIR / "dataset-mini.xml"
RICH_SAMPLE = SAMPLES_DIR / "ccmm_sample.xml"
GACR = "01pv73b02"  # Grantová agentura České republiky, ROR
CUNI = "024d6js02"  # Univerzita Karlova, ROR
MUNI = "02j46qs45"  # Masarykova Univerzita, ROR


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    # vocabularies.yaml maps vocabulary types to data files; subjects go to their own service
    VocabulariesFixture(system_identity, FIXTURES / "vocabularies.yaml", delay=False).load()
    # the RORs of the samples - the funder and the affiliations are kept by their vocabulary ids
    current_service_registry.get("funders").create(
        system_identity,
        {
            "id": GACR,
            "name": "Grantová agentura České republiky",
            "identifiers": [{"identifier": GACR, "scheme": "ror"}],
        },
    )
    for ror, name in ((CUNI, "Univerzita Karlova"), (MUNI, "Masarykova Univerzita")):
        current_service_registry.get("affiliations").create(
            system_identity, {"id": ror, "name": name, "identifiers": [{"identifier": ror, "scheme": "ror"}]}
        )
    current_search.flush_and_refresh("*")


@pytest.fixture(scope="module")
def client(app, database):
    from invenio_accounts.testutils import create_test_user, login_user_via_session

    user = create_test_user("test@example.org")
    client = app.test_client()
    with app.test_request_context():
        login_user_via_session(client, user=user)
    return client


def drop_expanded_affiliation_identifiers(record: dict) -> None:
    """Drop the affiliation identifiers expanded from the vocabulary on read, as a client does.

    They are dump only in RDM (AffiliationRelationSchema) - of the creators, contributors and the
    agents of the metadata records.
    """
    metadata = record["metadata"]
    creatibutors = [
        *metadata["creators"],
        *metadata.get("contributors", []),
        *(agent for mr in metadata.get("metadata_identifications", []) for agent in mr["qualified_relations"]),
    ]
    for creatibutor in creatibutors:
        for affiliation in creatibutor.get("affiliations", []):
            affiliation.pop("identifiers", None)


@pytest.fixture(scope="module")
def headers():
    return {"Content-Type": CCMM_XML_MIMETYPE, "Accept": "application/json"}


def test_import_ccmm_xml(client, headers, vocabularies, location):
    response = client.post("/ccmm-dataset", headers=headers, data=SAMPLE.read_bytes())
    assert response.status_code == 201, response.get_data(as_text=True)
    body = response.get_json()
    assert body["metadata"]["publication_date"] == "2024-05-01"  # the Created time reference
    # the source xml is kept on the record
    assert body["ccmm_xml"] == SAMPLE.read_text(encoding="utf-8")
    assert not body.get("errors")


def test_import_export_round_trip(client, headers, vocabularies, location):
    # import the sample - the draft must be clean already here (publishing just repeats the validation)
    response = client.post("/ccmm-dataset", headers=headers, data=RICH_SAMPLE.read_bytes())
    assert response.status_code == 201, response.get_data(as_text=True)
    record = response.get_json()
    assert not record.get("errors")
    # the rors in the vocabularies are the ids of the funder and the affiliation
    assert record["metadata"]["funding"][0]["funder"]["id"] == GACR
    assert record["metadata"]["creators"][0]["affiliations"][0]["id"] == CUNI

    # no files are uploaded here - mark the draft as metadata-only ...
    record["files"] = {"enabled": False}
    drop_expanded_affiliation_identifiers(record)
    response = client.put(
        f"/ccmm-dataset/{record['id']}/draft",
        json=record,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert not response.get_json().get("errors")

    # ... publish the draft - the source xml is kept on the published record and its edit draft ...
    response = client.post(f"/ccmm-dataset/{record['id']}/draft/actions/publish")
    assert response.status_code == 202, response.get_data(as_text=True)
    assert response.get_json()["ccmm_xml"] == RICH_SAMPLE.read_text(encoding="utf-8")
    response = client.post(f"/ccmm-dataset/{record['id']}/draft")
    assert response.status_code == 201, response.get_data(as_text=True)
    assert response.get_json()["ccmm_xml"] == RICH_SAMPLE.read_text(encoding="utf-8")

    # ... export the record back to ccmm xml ...
    response = client.get(f"/ccmm-dataset/{record['id']}", headers={"Accept": CCMM_XML_MIMETYPE})
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.mimetype == CCMM_XML_MIMETYPE
    exported_xml = response.get_data(as_text=True)
    # the sample has no Created time reference - publication_year is used
    assert "<publication_year>2025</publication_year>" in exported_xml
    # the metadata were created in the original repository of the sample - its iri and repository are kept
    (metadata_record,) = convert_xml_to_json(exported_xml)[0]["metadata_identification"]
    assert metadata_record["iri"] == "https://original-repository.cz/dataset_metadata_id"
    assert metadata_record["original_repository"] == {"iri": "https://original-repository.cz"}
    # the data manager of the metadata record (a contributor in the record) is back there
    (data_manager,) = metadata_record["qualified_relation"]
    assert data_manager["relation"]["person"]["family_name"] == ["Novák"]
    # the rors are exported back
    exported = convert_xml_to_json(exported_xml)[0]
    (funder,) = exported["funding_reference"][0]["funder"]
    assert [identifier["value"] for identifier in funder["organization"]["identifier"]] == [GACR]
    (affiliation,) = exported["qualified_relation"][0]["relation"]["person"]["affiliation"]
    assert [identifier["value"] for identifier in affiliation["identifier"]] == [CUNI]

    # ... and import the exported xml again - the metadata round trips
    response = client.post("/ccmm-dataset", headers=headers, data=exported_xml.encode())
    assert response.status_code == 201, response.get_data(as_text=True)
    assert response.get_json()["metadata"]["publication_date"] == record["metadata"]["publication_date"]


def test_import_invalid_ccmm_xml_is_400(client, headers, vocabularies, location):
    response = client.post("/ccmm-dataset", headers=headers, data=b"<dataset>not a ccmm dataset</dataset>")
    assert response.status_code == 400, response.get_data(as_text=True)


def test_model_imports_registered():
    imports = {imp.code: imp for imp in ccmm_dataset.imports}
    assert imports["ccmm-xml"].mimetype == CCMM_XML_MIMETYPE
    assert imports["ccmm-xml"].oai_name == ("https://schema.ccmm.cz/research-data/1.1", "dataset")


def stored_related_identifiers(record_id: str) -> list[tuple[str, str, str]]:
    """Return the related identifiers of the draft as the service has them (the RDM features use this)."""
    service = ccmm_dataset.proxies.current_service
    draft = service.read_draft(system_identity, record_id).to_dict()
    return [
        (ri["identifier"], ri["scheme"], ri["relation_type"]["id"])
        for ri in draft["metadata"].get("related_identifiers", [])
    ]


def test_related_identifiers_from_related_resources(client, headers, vocabularies, location):
    response = client.post("/ccmm-dataset", headers=headers, data=RICH_SAMPLE.read_bytes())
    assert response.status_code == 201, response.get_data(as_text=True)
    record = response.get_json()

    # the related identifiers are made from the related resources (their iri and resource url here)
    related_identifiers = stored_related_identifiers(record["id"])
    assert related_identifiers[:3] == [
        ("http://data.europa.eu/eli/dir/2008/50/oj", "url", "isreferencedby"),
        (
            "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32008L0050&qid=1754039487879",
            "url",
            "isreferencedby",
        ),
        (
            "https://www.envitech-bohemia.cz/p/264/envi-lvs1-sampler-pro-odber-prasneho-aerosolu",
            "url",
            "iscollectedby",
        ),
    ]
    assert len(related_identifiers) == 6

    # ... but they are not sent to the api clients (json) - the related resources are
    assert "related_identifiers" not in record["metadata"]
    assert record["metadata"]["related_resources"]
    # the ui json (read only) keeps them
    ui = client.get(
        f"/ccmm-dataset/{record['id']}/draft", headers={"Accept": "application/vnd.inveniordm.v1+json"}
    ).get_json()
    assert len(ui["metadata"]["related_identifiers"]) == 6

    # on update, the related identifiers sent by the client are overwritten by the related resources
    record["metadata"]["related_resources"] = [
        {"title": "An article", "relation_type": {"id": "cites"}, "iri": "https://doi.org/10.1234/abc"}
    ]
    record["metadata"]["related_identifiers"] = [
        {"identifier": "https://example.org/x", "scheme": "url", "relation_type": {"id": "isreferencedby"}}
    ]
    drop_expanded_affiliation_identifiers(record)
    response = client.put(
        f"/ccmm-dataset/{record['id']}/draft",
        json=record,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert "related_identifiers" not in response.get_json()["metadata"]
    assert stored_related_identifiers(record["id"]) == [("10.1234/abc", "doi", "cites")]


def test_preset_alias():
    from ccmm_invenio.models import ccmm_preset_1_1_0, ccmm_production_preset_1_1_0

    assert ccmm_production_preset_1_1_0 is ccmm_preset_1_1_0

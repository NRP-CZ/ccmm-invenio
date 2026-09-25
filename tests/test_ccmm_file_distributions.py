#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Files of a record exported as ccmm downloadable file distributions."""

from __future__ import annotations

from typing import Any

import pytest
from oarepo_runtime import current_runtime

from ccmm_invenio.resources.serializers import CCMMXMLSerializer
from ccmm_invenio.resources.serializers.ccmm.converter import CCMM_XML_MIMETYPE, convert_xml_to_json
from tests.test_ccmm_import_http import SAMPLE, client, headers, vocabularies  # noqa: F401 - fixtures

FILE_KEY = "data file.pdf"
FILE_CONTENT = b"%PDF-1.4 test"


def publish_with_file(client, headers, files_access: str) -> dict[str, Any]:  # noqa: F811 - fixture
    """Import the minimal sample, upload a file and publish, return the record (as the owner)."""
    record = client.post("/ccmm-dataset", headers=headers, data=SAMPLE.read_bytes()).get_json()
    record["access"]["files"] = files_access
    response = client.put(f"/ccmm-dataset/{record['id']}/draft", json=record)
    assert response.status_code == 200, response.get_data(as_text=True)
    files_url = f"/ccmm-dataset/{record['id']}/draft/files"
    assert client.post(files_url, json=[{"key": FILE_KEY}]).status_code == 201
    response = client.put(
        f"{files_url}/{FILE_KEY}/content", data=FILE_CONTENT, headers={"Content-Type": "application/octet-stream"}
    )
    assert response.status_code == 200
    assert client.post(f"{files_url}/{FILE_KEY}/commit").status_code == 200
    response = client.post(f"/ccmm-dataset/{record['id']}/draft/actions/publish")
    assert response.status_code == 202, response.get_data(as_text=True)
    return response.get_json()


def exported_files(xml: str) -> list[dict[str, Any]]:
    """Return the downloadable file distributions of an exported ccmm xml."""
    exported, errors = convert_xml_to_json(xml)
    # the known gaps of the export (access_rights, metadata_identification), not the distributions
    assert not [e for e in errors if "distribution" in str(e)]
    return [d["distribution_downloadable_file"] for d in exported.get("distribution", [])]


def export(some_client, record_id: str) -> list[dict[str, Any]]:
    response = some_client.get(f"/ccmm-dataset/{record_id}", headers={"Accept": CCMM_XML_MIMETYPE})
    assert response.status_code == 200, response.get_data(as_text=True)
    return exported_files(response.get_data(as_text=True))


def test_public_files(app, client, headers, vocabularies, location):  # noqa: F811 - fixtures
    record = publish_with_file(client, headers, "public")
    # the download url is the content link of the file, as invenio has it
    files = client.get(f"/ccmm-dataset/{record['id']}/files").get_json()
    (file_entry,) = files["entries"]

    (file,) = export(app.test_client(), record["id"])  # anonymous
    assert file["title"] == FILE_KEY
    assert file["access_url"] == [{"iri": record["links"]["self_html"]}]
    assert file["download_url"] == [{"iri": file_entry["links"]["content"]}]
    assert file["byte_size"] == len(FILE_CONTENT)
    assert file["format"]["iri"] == "http://publications.europa.eu/resource/authority/file-type/PDF"
    assert file["media_type"]["iri"] == "http://www.iana.org/assignments/media-types/application/pdf"
    assert file["checksum"] == {
        "checksum_value": file_entry["checksum"].removeprefix("md5:").upper(),  # xs:hexBinary, upper case
        "algorithm": {"iri": "http://spdx.org/rdf/terms#checksumAlgorithm_md5", "label": [{"lang": "en", "$": "MD5"}]},
    }


def test_restricted_files(app, client, headers, vocabularies, location):  # noqa: F811 - fixtures
    record = publish_with_file(client, headers, "restricted")
    # the public may see the record, but not the files - they are not advertised
    assert export(app.test_client(), record["id"]) == []
    # the owner may read the files
    assert [file["title"] for file in export(client, record["id"])] == [FILE_KEY]


@pytest.mark.parametrize(("files_access", "exported"), [("public", [FILE_KEY]), ("restricted", [])])
def test_oai(client, headers, vocabularies, location, files_access, exported):  # noqa: F811 - fixtures
    record = publish_with_file(client, headers, files_access)
    # oai-pmh serializes the record loaded from its search index dump
    model = current_runtime.models_by_schema[record["$schema"]]
    source = model.record_cls.pid.resolve(record["id"]).dumps()
    xml = CCMMXMLSerializer().serialize_object(model.record_cls.loads(source))
    assert [file["title"] for file in exported_files(xml)] == exported


@pytest.mark.parametrize(
    ("files_access", "iri"),
    [
        ("public", "http://purl.org/coar/access_right/c_abf2"),  # open
        ("restricted", "http://purl.org/coar/access_right/c_16ec"),  # restricted
    ],
)
def test_access_rights(app, client, headers, vocabularies, location, files_access, iri):  # noqa: F811 - fixtures
    record = publish_with_file(client, headers, files_access)
    assert record["access"]["status"] == ("open" if files_access == "public" else "restricted")
    response = app.test_client().get(f"/ccmm-dataset/{record['id']}", headers={"Accept": CCMM_XML_MIMETYPE})
    exported, _errors = convert_xml_to_json(response.get_data(as_text=True))
    assert exported["terms_of_use"]["access_rights"]["iri"] == iri

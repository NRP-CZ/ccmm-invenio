#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""The exports registered on the ccmm model (the RDM complete set minus marcxml/dcat, plus ccmm-xml)."""

from __future__ import annotations

import pytest

from tests.model import ccmm_dataset
from tests.test_ccmm_import_http import SAMPLE, client, headers, vocabularies  # noqa: F401 - fixtures


def test_rdm_exports_registered(app):
    codes = {export.code for export in ccmm_dataset.exports}
    # the RDM complete set ...
    assert {
        "json",
        "ui_json",
        "jsonld",
        "csv-full",
        "csv-simple",
        "csl",
        "geojson",
        "datacite-xml",
        "datapackage",
        "dublincore",
        "citation",
        "bibtex",
        "marcxml",
        "dcat",
    } <= codes
    # ... plus ccmm-xml
    assert "ccmm-xml" in codes


def publish_sample(client, headers) -> str:  # noqa: F811 - fixtures
    """Import the ccmm sample as a metadata-only record and publish it."""
    record = client.post("/ccmm-dataset", headers=headers, data=SAMPLE.read_bytes()).get_json()
    record["files"] = {"enabled": False}
    response = client.put(
        f"/ccmm-dataset/{record['id']}/draft",
        json=record,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    response = client.post(f"/ccmm-dataset/{record['id']}/draft/actions/publish")
    assert response.status_code == 202, response.get_data(as_text=True)
    return record["id"]


# the signposting linkset exports of the oarepo baseline fail on the model lookup
# (a pre-existing problem, unrelated to the RDM exports added here)
SIGNPOSTING = {"lset", "jsonlset"}

# marcxml, dcat and datacite-xml index subject["subject"] (the expanded title) and subjects
# are not expanded in this model yet (only {"id"} arrives) - they fail until oarepo-rdm
# expands the subjects relation
NEEDS_SUBJECT_EXPANSION = {"marcxml", "dcat", "datacite-xml"}


@pytest.mark.parametrize(
    "export",
    [export for export in ccmm_dataset.exports if export.code not in SIGNPOSTING | NEEDS_SUBJECT_EXPANSION],
    ids=lambda export: export.code,
)
def test_export_serializes(client, headers, vocabularies, location, export):  # noqa: F811 - fixtures
    """Every registered export serializes the published ccmm sample without an error."""
    record_id = publish_sample(client, headers)
    response = client.get(f"/ccmm-dataset/{record_id}", headers={"Accept": export.mimetype})
    assert response.status_code == 200, f"{export.code}: {response.get_data(as_text=True)[:500]}"
    assert response.get_data(as_text=True), export.code


@pytest.mark.parametrize(
    "export",
    [export for export in ccmm_dataset.exports if export.code in NEEDS_SUBJECT_EXPANSION],
    ids=lambda export: export.code,
)
@pytest.mark.xfail(
    strict=True,
    reason="subject titles not expanded yet; drop from NEEDS_SUBJECT_EXPANSION when oarepo-rdm expands them",
)
def test_export_serializes_after_subject_expansion(client, headers, vocabularies, location, export):  # noqa: F811
    """Guard: an XPASS here means oarepo-rdm expands subjects - remove the export from the skip set above."""
    record_id = publish_sample(client, headers)
    response = client.get(f"/ccmm-dataset/{record_id}", headers={"Accept": export.mimetype})
    assert response.status_code == 200, response.get_data(as_text=True)[:500]

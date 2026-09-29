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

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import RelatedResourceSchema

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)

schema = RelatedResourceSchema()


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    for vocabulary_type, pid_type in (
        ("identifierschemes", "idsch"),
        ("resourcetypes", "rsrct"),
        ("relationtypes", "rlt"),
        ("contributorsroles", "cor"),
    ):
        vocab_service.create_type(system_identity, vocabulary_type, pid_type)
        data_file = "resourceagentroletypes" if vocabulary_type == "contributorsroles" else vocabulary_type
        for entry in yaml.safe_load((FIXTURES / f"{data_file}.yaml").read_text(encoding="utf-8")):
            vocab_service.create(system_identity, {"type": vocabulary_type, **entry})
    vocab_service.indexer.refresh()


def related_resources(sample: str) -> list:
    data, errors = convert_xml_to_json((SAMPLES_DIR / sample).read_text(encoding="utf-8"))
    assert errors == []
    return data["related_resource"]


def test_ccmm_sample(vocabularies):
    referenced_by, collected_by, derived_from, has_metadata = related_resources("ccmm_sample.xml")

    loaded = schema.load(referenced_by)
    assert loaded["resource_type"] == {"id": "c_18cf"}  # COAR "text"
    assert loaded["relation_type"] == {"id": "isreferencedby"}

    # an iri not in the vocabulary (here with a trailing slash) is an error
    with pytest.raises(ValidationError) as excinfo:
        schema.load({**referenced_by, "resource_type": {"iri": "http://purl.org/coar/resource_type/c_18cf/"}})
    assert "resource_type" in excinfo.value.messages

    assert schema.load(collected_by) == {
        "title": "ENVI LVS1 Sampler pro odběr prašného aerosolu",
        "resource_type": {"id": "instrument"},
        "relation_type": {"id": "iscollectedby"},
        "resource_url": "https://www.envitech-bohemia.cz/p/264/envi-lvs1-sampler-pro-odber-prasneho-aerosolu",
    }

    loaded = schema.load(derived_from)
    assert loaded["relation_type"] == {"id": "isderivedfrom"}
    # iri and resource_url are kept as they are, not added to the identifiers
    assert loaded["iri"] == "https://opendata.chmi.cz/air_quality/now/data/"
    assert loaded["resource_url"] == "https://opendata.chmi.cz/air_quality/"
    assert "identifiers" not in loaded

    assert schema.load(has_metadata)["relation_type"] == {"id": "hasmetadata"}


def test_identifier_iri_and_resource_url(vocabularies):
    (article,) = related_resources("dmq82-ed856.xml")
    loaded = schema.load(article)
    # the identifier, the iri and the resource_url (the same doi) are each kept in their own field
    assert loaded["identifiers"] == [{"identifier": "10.1007/s12540-025-01953-4", "scheme": "doi"}]
    assert loaded["iri"] == article["iri"]
    assert loaded["resource_url"] == article["resource_url"]
    assert loaded["resource_type"] == {"id": "publication-article"}
    assert loaded["relation_type"] == {"id": "isreferencedby"}


def test_title_from_iri(vocabularies):
    # the title is required in the model - the iri, or the resource url, when there is none
    assert schema.load({"iri": "https://doi.org/10.1234/abc"}) == {
        "title": "https://doi.org/10.1234/abc",
        "iri": "https://doi.org/10.1234/abc",
    }
    assert schema.load({"resource_url": "https://x.cz/a"}) == {
        "title": "https://x.cz/a",
        "resource_url": "https://x.cz/a",
    }


def test_round_trip(vocabularies):
    (article,) = related_resources("dmq82-ed856.xml")
    loaded = schema.load(article)
    dumped = schema.dump(loaded)

    _xml, errors = XMLToGenericJSONConverter().json_to_xml(
        ccmm_1_1_0_schema, dumped, f"{{{NS_CCMM_1_1_0}}}related_resource"
    )
    assert errors == []
    # the doi identifier carries the iri of the resource; the iri and resource_url are dumped as they are
    assert dumped["identifier"][0]["iri"] == "https://doi.org/10.1007/s12540-025-01953-4"
    assert dumped["iri"] == article["iri"]
    assert dumped["resource_url"] == article["resource_url"]
    assert schema.load(dumped) == loaded

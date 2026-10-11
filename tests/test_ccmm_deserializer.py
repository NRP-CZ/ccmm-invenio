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
from lxml import etree
from marshmallow import ValidationError

from ccmm_invenio.resources.deserializers.ccmm import CCMMJSONDeserializer
from ccmm_invenio.resources.serializers.ccmm.converter import NS_CCMM_1_1_0, convert_xml_to_json

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
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
        ("resourcetypes", "rsrct", "resourcetypes"),
        ("accessrights", "v-ar", "accessrights"),
        ("contributorsroles", "cor", "resourceagentroletypes"),
    ):
        vocab_service.create_type(system_identity, vocabulary_type, pid_type)
        for entry in yaml.safe_load((FIXTURES / f"{data_file}.yaml").read_text(encoding="utf-8")):
            vocab_service.create(system_identity, {"type": vocabulary_type, **entry})
    vocab_service.indexer.refresh()


def test_deserialize_xml_element(vocabularies):
    """A parsed element (OAI-PMH harvester) loads as the same record as the xml string (REST import)."""
    xml = SAMPLE.read_text(encoding="utf-8")
    element = etree.fromstring(xml.encode("utf-8"))

    from_element = CCMMJSONDeserializer().deserialize_xml(element)
    from_string = CCMMJSONDeserializer().deserialize(xml)

    # ccmm_xml is the element serialized back - a string, not the element
    ccmm_xml = from_element.pop("ccmm_xml")
    assert isinstance(ccmm_xml, str)
    assert from_string.pop("ccmm_xml") == xml
    assert from_element == from_string
    # ... with the same content as the source xml
    assert convert_xml_to_json(ccmm_xml)[0] | {"ccmm_xml": None} == convert_xml_to_json(xml)[0] | {"ccmm_xml": None}


def test_deserialize_xml_invalid_element():
    element = etree.fromstring(f'<dataset xmlns="{NS_CCMM_1_1_0}"><title>Incomplete</title></dataset>'.encode())
    with pytest.raises(ValidationError):
        CCMMJSONDeserializer().deserialize_xml(element)

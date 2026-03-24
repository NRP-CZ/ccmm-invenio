#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

from ccmm_invenio.serializers.production.ccmm_xml import CCMMProductionXMLSerializer_1_1_0
from tests.model import production_dataset


def canonicalize(xml_string):
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_string.encode(), parser)
    return etree.tostring(root, method="c14n")


def test_exporter(app, db, identity_simple, search_clear, location, vocab_fixtures):
    exports = production_dataset.exports
    ccmm_xml_in_exports = False
    for ex in exports:
        if ex.name == "CCMM XML Export":
            ccmm_xml_in_exports = True

    assert ccmm_xml_in_exports

    serializer = CCMMProductionXMLSerializer_1_1_0()

    file_path = Path(__file__).parent / "data" / "2026-01-29_example.json"

    with file_path.open("r", encoding="utf-8") as f:
        example_data = json.load(f)

    serialized_record = serializer.serialize_object(example_data)

    expected_xml = """<?xml version='1.0' encoding='utf-8'?>
    <ccmm:dataset xmlns:ccmm="https://schema.ccmm.cz/research-data/1.1">
      <ccmm:title>Kvalita ovzduší ve středních čechách 2024</ccmm:title>
      <ccmm:qualified_relation>
        <ccmm:relation>
          <ccmm:person>
            <ccmm:name>Novák, Jan</ccmm:name>
            <ccmm:given_name>Jan</ccmm:given_name>
            <ccmm:family_name>Novák</ccmm:family_name>
            <ccmm:affiliation>
              <ccmm:organization>
                <ccmm:name>Univerzita Karlova</ccmm:name>
              </ccmm:organization>
            </ccmm:affiliation>
          </ccmm:person>
        </ccmm:relation>
        <ccmm:role>
          <ccmm:iri>Other</ccmm:iri>
        </ccmm:role>
      </ccmm:qualified_relation>
      <ccmm:publication_year>2025</ccmm:publication_year>
      <ccmm:primary_language>
        <ccmm:iri>https://id.loc.gov/vocabulary/iso639-2/cze</ccmm:iri>
        <ccmm:label xml:lang="cs">čeština</ccmm:label>
        <ccmm:label xml:lang="en">Czech</ccmm:label>
      </ccmm:primary_language>
      <ccmm:other_language>
        <ccmm:iri>https://id.loc.gov/vocabulary/iso639-2/eng</ccmm:iri>
        <ccmm:label xml:lang="cs">angličtina</ccmm:label>
        <ccmm:label xml:lang="en">English</ccmm:label>
      </ccmm:other_language>
      <ccmm:time_reference>
        <ccmm:temporal_representation>
          <ccmm:time_instant>
            <ccmm:date>2025-04-27</ccmm:date>
          </ccmm:time_instant>
        </ccmm:temporal_representation>
        <ccmm:date_type>
          <ccmm:iri>Collected</ccmm:iri>
        </ccmm:date_type>
        <ccmm:date_information xml:lang="en">Date collected</ccmm:date_information>
      </ccmm:time_reference>
      <ccmm:time_reference>
        <ccmm:temporal_representation>
          <ccmm:time_instant>
            <ccmm:date>2024-01-01</ccmm:date>
          </ccmm:time_instant>
        </ccmm:temporal_representation>
        <ccmm:date_type>
          <ccmm:iri>Collected</ccmm:iri>
        </ccmm:date_type>
        <ccmm:date_information xml:lang="en">Collection period</ccmm:date_information>
      </ccmm:time_reference>
    </ccmm:dataset>
    """

    assert canonicalize(serialized_record) == canonicalize(expected_xml)


def test_create(app, db, identity_simple, search_clear, location, vocab_fixtures):
    service = production_dataset.proxies.current_service

    rec = service.create(
        identity_simple,
        data={
            "metadata": {
                "title": "test",
                "publication_date": "2022-01-01",
                "resource_type": {"id": "dataset"},
                "creators": [
                    {
                        "person_or_org": {
                            "type": "personal",
                            "given_name": "John",
                            "family_name": "Doe",
                        }
                    }
                ],
            }
        },
    ).to_dict()

    assert rec.get("errors", []) == []

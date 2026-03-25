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
<dataset xmlns:ccmm="https://schema.ccmm.cz/research-data/1.1">
  <title>Kvalita ovzduší ve středních čechách 2024</title>
  <qualified_relation>
    <relation>
      <person>
        <name>Novák, Jan</name>
        <given_name>Jan</given_name>
        <family_name>Novák</family_name>
        <affiliation>
          <organization>
            <name>Univerzita Karlova</name>
          </organization>
        </affiliation>
      </person>
    </relation>
    <role>
      <iri>Other</iri>
    </role>
  </qualified_relation>
  <publication_year>2025</publication_year>
  <primary_language>
    <iri>http://publications.europa.eu/resource/authority/language/CES</iri>
  </primary_language>
  <other_language>
    <iri>http://publications.europa.eu/resource/authority/language/ENG</iri>
  </other_language>
  <time_reference>
    <temporal_representation>
      <time_instant>
        <date>2025-04-27</date>
      </time_instant>
    </temporal_representation>
    <date_type>
      <iri>Collected</iri>
    </date_type>
    <date_information xml:lang="en">Date collected</date_information>
  </time_reference>
  <time_reference>
    <temporal_representation>
      <time_instant>
        <date>2024</date>
      </time_instant>
    </temporal_representation>
    <date_type>
      <iri>Collected</iri>
    </date_type>
    <date_information xml:lang="en">Collection period</date_information>
  </time_reference>
</dataset>
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

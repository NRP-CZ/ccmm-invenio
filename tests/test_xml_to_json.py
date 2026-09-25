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
from typing import Any

import pytest
from xmlschema.validators import XsdComplexType

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    NS_GML,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_json_to_xml,
    convert_xml_to_json,
)

SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
SAMPLE = SAMPLES_DIR / "ccmm_sample.xml"


def _without_gml(data: Any) -> Any:
    """Replace gml serialized as xml strings with a placeholder."""
    if isinstance(data, dict):
        return {k: _without_gml(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_without_gml(v) for v in data]
    if isinstance(data, str) and f'xmlns:gml="{NS_GML}"' in data:
        return "<gml>"
    return data


def _without_ccmm_xml(data: Any) -> Any:
    """Drop the ccmm_xml field - it is the source xml itself, different after a round trip."""
    return {k: v for k, v in _without_gml(data).items() if k != "ccmm_xml"}


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_round_trip(sample):
    data, errors = convert_xml_to_json(sample.read_text(encoding="utf-8"))
    assert errors == []

    xml, errors = convert_json_to_xml(data)
    assert errors == []

    round_tripped, errors = convert_xml_to_json(xml)
    assert errors == []
    # xml schema always fills in fixed attributes (xlink:type="simple" inside gml),
    # so gml strings may differ after the first round trip ...
    assert _without_ccmm_xml(round_tripped) == _without_ccmm_xml(data)
    # ... but the conversion is stable from then on
    assert convert_xml_to_json(convert_json_to_xml(round_tripped)[0])[0] == round_tripped


def test_gml_is_kept_as_xml_string():
    data, errors = convert_xml_to_json(SAMPLE.read_text(encoding="utf-8"))

    assert errors == []
    location = data["location"][0]
    assert location["bounding_box"][0].startswith("<bounding_box ")
    assert "<gml:lowerCorner>" in location["bounding_box"][0]
    # names in other than the ccmm namespace are "{namespace}local" in the json
    assert location["geometry"][f"{{{NS_GML}}}MultiSurface"].startswith("<gml:MultiSurface ")
    # non-gml content is still converted to json
    assert data["alternate_title"][0]["title"] == [
        {"lang": "en", "$": "Air quality measurements in Central Bohemian Region in 2024."}
    ]
    # the source xml is kept in the json
    assert data["ccmm_xml"] == SAMPLE.read_text(encoding="utf-8")


def test_no_attribute_element_conflicts():
    # attributes are converted without prefix, so they must not clash with sibling elements.
    # Only ccmm types are checked - gml (and xlink used by gml) is kept as an xml string.
    converter = XMLToGenericJSONConverter()
    conflicts = {}
    for xsd_type in ccmm_1_1_0_schema.maps.iter_components():
        if not isinstance(xsd_type, XsdComplexType) or xsd_type.target_namespace != NS_CCMM_1_1_0:
            continue
        attributes = {converter.map_qname(name) for name in xsd_type.attributes if name}
        elements = (
            {converter.map_qname(el.name) for el in xsd_type.content.iter_elements() if el.name}
            if xsd_type.has_complex_content()
            else set()
        )
        if attributes & elements:
            conflicts[xsd_type.name] = attributes & elements
    assert conflicts == {}

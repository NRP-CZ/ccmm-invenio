#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests for ``ccmm_invenio.serializers.production.ccmm.CCMMSerializer``.

Organized bottom-up, mirroring the section order of ``ccmm.py`` itself: plain data-only
helpers first, then one-element leaf serializers, then the composite methods that
assemble them, finishing with the top-level ``serialize()``/``serialize_dataset()``.

Every test that produces an ``lxml`` element:

1. builds it from a small, valid, hand-written JSON fragment (matching ``schema.json``),
2. asserts the serialized XML contains that input data, and
3. validates the element against the real CCMM XSD (see ``assert_schema_valid`` and
   ``tests/data/xsd/README.md`` for how a fragment -- as opposed to a whole document --
   gets validated in isolation).

``CCMMSerializer.serialize_vocabulary`` resolves every vocabulary type through the same
placeholder NMA IRI scheme for now (``https://nma.eosc.cz/vocabularies/{type}/{id}``) --
real, per-type resolution is expected to replace it later. That is exactly why tests
exercise the real ``CCMMSerializer`` directly rather than a fake: the placeholder already
gives deterministic, checkable output.
"""

# ruff: noqa: SLF001 -- this file deliberately tests private helpers too (per its brief:
# "meticulously add tests for each of the created methods, starting with the leaf ones").

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from lxml import etree

from ccmm_invenio.serializers.production.ccmm import XML_LANG, CCMMSerializer

CCMM_NS = "https://schema.ccmm.cz/research-data/1.1"

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def serializer() -> CCMMSerializer:
    """Build a fresh ``CCMMSerializer`` for each test."""
    return CCMMSerializer()


@pytest.fixture(scope="module")
def schema() -> etree.XMLSchema:
    """Load the offline test copy of the CCMM XSD (see ``tests/data/xsd/README.md``)."""
    return etree.XMLSchema(etree.parse(str(DATA_DIR / "xsd" / "ccmm-1.1.0-test.xsd")))


def xml(element: etree._Element) -> str:
    """Serialize `element` to a string, for substring ("contains the input data") assertions."""
    return etree.tostring(element, encoding="unicode")


def as_global_element(element: etree._Element, global_name: str) -> etree._Element:
    """Return a copy of `element` renamed to the CCMM-namespaced global element `global_name`.

    A few CCMM elements are declared *locally*, under a different name than the global
    element that happens to share their type -- e.g. ``dataset``'s local
    ``qualified_relation`` shares its type with the global ``resource_to_agent_relationship``
    element. The XSD only exposes global elements as validation entry points, and an
    element's content model is defined by its type, not its tag, so renaming to a
    same-typed global element is how such a fragment is validated in isolation.
    """
    renamed = deepcopy(element)
    renamed.tag = f"{{{CCMM_NS}}}{global_name}"
    return renamed


def assert_valid_apart_from(schema: etree.XMLSchema, element: etree._Element, *known_gaps: str) -> None:
    """Assert `element` is invalid *only* because of the given, already-documented `known_gaps`.

    Used for the handful of elements ``CCMMSerializer`` can never fully complete
    because schema.json has no source data for one of their required children (see
    ccmm_export_plan.md) -- e.g. ``terms_of_use/access_rights``. Checks the schema
    validator's error log rather than the element's overall validity so that any *other*,
    unexpected structural error still fails the test.
    """
    is_valid = schema.validate(element)
    unexpected_errors = [str(error) for error in schema.error_log if not any(gap in str(error) for gap in known_gaps)]
    assert unexpected_errors == []
    assert not is_valid  # sanity check that `known_gaps` is still accurate (and still needed)


# ---------------------------------------------------------------------------
# Small generic helpers
# ---------------------------------------------------------------------------


def test_append_text_appends_when_value_present(serializer: CCMMSerializer) -> None:
    parent = etree.Element("root")
    el = serializer._append_text(parent, serializer.ns.title, "hello")
    assert el is not None
    assert el.tag == str(serializer.ns.title)
    assert el.text == "hello"
    assert "hello" in xml(parent)


@pytest.mark.parametrize("value", [None, ""])
def test_append_text_does_nothing_for_falsy_value(serializer: CCMMSerializer, value: str | None) -> None:
    parent = etree.Element("root")
    assert serializer._append_text(parent, serializer.ns.title, value) is None
    assert len(parent) == 0


def test_append_i18n_text_sets_xml_lang(serializer: CCMMSerializer) -> None:
    parent = etree.Element("root")
    el = serializer._append_i18n_text(parent, serializer.ns.title, "cs", "Ahoj")
    assert el is not None
    assert el.text == "Ahoj"
    assert el.get(XML_LANG) == "cs"
    assert "Ahoj" in xml(parent)


def test_append_i18n_text_defaults_missing_lang_to_und(serializer: CCMMSerializer) -> None:
    parent = etree.Element("root")
    el = serializer._append_i18n_text(parent, serializer.ns.title, None, "Ahoj")
    assert el is not None
    assert el.get(XML_LANG) == "und"


def test_append_i18n_text_does_nothing_for_falsy_value(serializer: CCMMSerializer) -> None:
    parent = etree.Element("root")
    assert serializer._append_i18n_text(parent, serializer.ns.title, "cs", None) is None
    assert len(parent) == 0


def test_group_by_type_groups_entries_sharing_the_same_type(serializer: CCMMSerializer) -> None:
    entries = [
        {"title": "A", "type": {"id": "T1"}, "lang": {"id": "en"}},
        {"title": "B", "type": {"id": "T1"}, "lang": {"id": "cs"}},
        {"title": "C", "type": {"id": "T2"}, "lang": {"id": "en"}},
    ]
    groups = serializer._group_by_type(entries, text_key="title")
    assert groups == [
        {"type": {"id": "T1"}, "items": [{"lang": "en", "value": "A"}, {"lang": "cs", "value": "B"}]},
        {"type": {"id": "T2"}, "items": [{"lang": "en", "value": "C"}]},
    ]


def test_group_by_type_groups_entries_with_no_type_together(serializer: CCMMSerializer) -> None:
    entries = [
        {"title": "A", "type": None, "lang": None},
        {"title": "B", "type": None, "lang": None},
    ]
    groups = serializer._group_by_type(entries, text_key="title")
    assert len(groups) == 1
    assert groups[0]["type"] is None
    assert [item["value"] for item in groups[0]["items"]] == ["A", "B"]


def test_group_by_type_empty_input(serializer: CCMMSerializer) -> None:
    assert serializer._group_by_type([], text_key="title") == []


@pytest.mark.parametrize(
    ("ccmm_lang", "bcp47_tag"),
    [
        ("ENG", "en"),
        ("CES", "cs"),  # terminology ISO 639-2 code
        ("CZE", "cs"),  # bibliographic ISO 639-2 code -- same language, different code
        ("fra", "fr"),  # lowercase input
    ],
)
def test_xml_lang_from_ccmm_lang_converts_known_codes(
    serializer: CCMMSerializer, ccmm_lang: str, bcp47_tag: str
) -> None:
    assert serializer.xml_lang_from_ccmm_lang(ccmm_lang) == bcp47_tag


@pytest.mark.parametrize("ccmm_lang", [None, "", "XXX"])
def test_xml_lang_from_ccmm_lang_returns_unk_for_falsy_or_unrecognized(
    serializer: CCMMSerializer, ccmm_lang: str | None
) -> None:
    # Never `None` -- `xml:lang` is required on every element this feeds into.
    assert serializer.xml_lang_from_ccmm_lang(ccmm_lang) == "unk"


# ---------------------------------------------------------------------------
# identifier / identifier_scheme
# ---------------------------------------------------------------------------


def test_serialize_identifier_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {"identifier": "10.1234/abc", "scheme": "doi"}
    el = serializer.serialize_identifier(entry)
    assert el.tag == str(serializer.ns.identifier)
    assert el.findtext(str(serializer.ns.value)) == "10.1234/abc"
    text = xml(el)
    assert "10.1234/abc" in text
    assert "doi" in text  # via the placeholder vocabulary IRI, see serialize_vocabulary
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# alternate_title (from additional_titles[])
# ---------------------------------------------------------------------------


def test_group_additional_titles_groups_by_type(serializer: CCMMSerializer) -> None:
    container = {
        "additional_titles": [
            {"title": "A", "type": {"id": "TranslatedTitle"}, "lang": {"id": "ENG"}},
            {"title": "B", "type": {"id": "TranslatedTitle"}, "lang": {"id": "CES"}},
        ]
    }
    groups = serializer.group_additional_titles(container)
    # `lang` is converted from the CCMM 3-letter code to a BCP 47 tag along the way, see
    # `xml_lang_from_ccmm_lang`.
    assert groups == [
        {
            "type": {"id": "TranslatedTitle"},
            "items": [{"lang": "en", "value": "A"}, {"lang": "cs", "value": "B"}],
        }
    ]


def test_group_additional_titles_empty(serializer: CCMMSerializer) -> None:
    assert serializer.group_additional_titles({}) == []


def test_serialize_alternate_title_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    # `lang` here is opaque to `serialize_alternate_title` -- it's set on `xml:lang` verbatim.
    # Converting a CCMM language id to a BCP 47 tag is `group_additional_titles`'s job (via
    # `_group_by_type`/`xml_lang_from_ccmm_lang`), tested separately above.
    group = {
        "type": {"id": "TranslatedTitle"},
        "items": [
            {"lang": "en", "value": "Air quality in 2024"},
            {"lang": "cs", "value": "Kvalita ovzduší 2024"},
        ],
    }
    el = serializer.serialize_alternate_title(group)
    assert el.tag == str(serializer.ns.alternate_title)
    titles = el.findall(str(serializer.ns.title))
    assert [t.text for t in titles] == ["Air quality in 2024", "Kvalita ovzduší 2024"]
    assert [t.get(XML_LANG) for t in titles] == ["en", "cs"]
    assert "TranslatedTitle" in xml(el)
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# description (from the single "description" field and from additional_descriptions[])
# ---------------------------------------------------------------------------


def test_serialize_description_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    group = {"type": {"id": "abstract"}, "items": [{"lang": "CES", "value": "Popis datové sady."}]}
    el = serializer.serialize_description(group)
    assert el.tag == str(serializer.ns.description)
    assert el.findtext(str(serializer.ns.description_text)) == "Popis datové sady."
    assert "abstract" in xml(el)
    schema.assertValid(el)


def test_serialize_descriptions_combines_main_and_additional(serializer: CCMMSerializer) -> None:
    metadata = {
        "description": "Main abstract",
        "additional_descriptions": [
            {"description": "Extra", "type": {"id": "abstract"}, "lang": {"id": "en"}},
        ],
    }
    descriptions = serializer.serialize_descriptions(metadata)
    assert len(descriptions) == 2
    assert descriptions[0].findtext(str(serializer.ns.description_text)) == "Main abstract"
    assert descriptions[1].findtext(str(serializer.ns.description_text)) == "Extra"


def test_serialize_descriptions_empty(serializer: CCMMSerializer) -> None:
    assert serializer.serialize_descriptions({}) == []


# ---------------------------------------------------------------------------
# Section: resource_to_agent_relationship, plus the agent choice, person and organization
# ---------------------------------------------------------------------------


def test_serialize_organization_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    organization = {"name": "Univerzita Karlova", "identifiers": [{"identifier": "12345", "scheme": "ror"}]}
    el = serializer.serialize_organization(organization)
    assert el.tag == str(serializer.ns.organization)
    assert el.findtext(str(serializer.ns.name)) == "Univerzita Karlova"
    text = xml(el)
    assert "Univerzita Karlova" in text
    assert "12345" in text
    schema.assertValid(el)


def test_serialize_person_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    person = {
        "name": "Novák, Jan",
        "given_name": "Jan",
        "family_name": "Novák",
        "identifiers": [{"identifier": "0000-0003-0852-6632", "scheme": "orcid"}],
    }
    el = serializer.serialize_person(person, affiliations=[{"name": "Univerzita Karlova"}])
    assert el.tag == str(serializer.ns.person)
    assert el.findtext(str(serializer.ns.name)) == "Novák, Jan"
    assert [e.text for e in el.findall(str(serializer.ns.given_name))] == ["Jan"]
    assert [e.text for e in el.findall(str(serializer.ns.family_name))] == ["Novák"]
    text = xml(el)
    assert "0000-0003-0852-6632" in text
    assert "Univerzita Karlova" in text
    schema.assertValid(el)


def test_serialize_person_splits_multi_word_given_and_family_names(serializer: CCMMSerializer) -> None:
    person = {"name": "x", "given_name": "Jan Maria", "family_name": "Novák Svoboda"}
    el = serializer.serialize_person(person)
    assert [e.text for e in el.findall(str(serializer.ns.given_name))] == ["Jan", "Maria"]
    assert [e.text for e in el.findall(str(serializer.ns.family_name))] == ["Novák", "Svoboda"]


def test_serialize_resource_to_agent_relationship_person(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {
        "person_or_org": {"name": "Novák, Jan", "type": "personal", "given_name": "Jan", "family_name": "Novák"},
        "affiliations": [{"name": "Univerzita Karlova"}],
    }
    el = serializer.serialize_resource_to_agent_relationship(entry, {"id": "Creator"})
    assert el.tag == str(serializer.ns.qualified_relation)
    relation = el.find(str(serializer.ns.relation))
    assert relation is not None
    assert relation.find(str(serializer.ns.person)) is not None
    text = xml(el)
    assert "Novák, Jan" in text
    assert "Creator" in text
    schema.assertValid(as_global_element(el, "resource_to_agent_relationship"))


def test_serialize_resource_to_agent_relationship_organization_drops_affiliations(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    entry = {
        "person_or_org": {"name": "Czech Hydrometeorological Institute", "type": "organizational"},
        # CCMM's `organization` type has no `affiliation` slot -- must be dropped.
        "affiliations": [{"name": "Should be dropped"}],
    }
    el = serializer.serialize_resource_to_agent_relationship(entry, {"id": "DataCollector"})
    relation = el.find(str(serializer.ns.relation))
    assert relation is not None
    assert relation.find(str(serializer.ns.organization)) is not None
    assert "Czech Hydrometeorological Institute" in xml(el)
    assert "Should be dropped" not in xml(el)
    schema.assertValid(as_global_element(el, "resource_to_agent_relationship"))


def test_serialize_qualified_relations_creators_then_contributors(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    container = {
        "creators": [{"person_or_org": {"name": "Creator One", "type": "personal"}}],
        "contributors": [
            {
                "role": {"id": "DataCollector"},
                "person_or_org": {"name": "Contributor One", "type": "personal"},
            }
        ],
    }
    relations = serializer.serialize_qualified_relations(container)
    assert len(relations) == 2
    assert "Creator One" in xml(relations[0])
    assert "Creator" in xml(relations[0])  # defaulted role, no explicit "role" given above
    assert "Contributor One" in xml(relations[1])
    assert "DataCollector" in xml(relations[1])
    for relation in relations:
        schema.assertValid(as_global_element(relation, "resource_to_agent_relationship"))


def test_serialize_qualified_relations_empty(serializer: CCMMSerializer) -> None:
    assert serializer.serialize_qualified_relations({}) == []


# ---------------------------------------------------------------------------
# publication_year / time_reference (from publication_date and dates[])
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("publication_date", "expected"),
    [("2025-04-27", "2025"), ("2024", "2024"), (None, None), ("", None)],
)
def test_extract_publication_year(
    serializer: CCMMSerializer, publication_date: str | None, expected: str | None
) -> None:
    assert serializer.extract_publication_year({"publication_date": publication_date}) == expected


def test_serialize_time_reference_from_date_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {"date": "2025-04-27", "type": {"id": "Collected"}, "description": "Date collected"}
    el = serializer.serialize_time_reference_from_date(entry)
    assert el.tag == str(serializer.ns.time_reference)
    date_path = f"{serializer.ns.temporal_representation}/{serializer.ns.time_instant}/{serializer.ns.date}"
    assert el.find(date_path).text == "2025-04-27"
    text = xml(el)
    assert "Collected" in text
    assert "Date collected" in text
    schema.assertValid(el)


def test_serialize_time_references_no_synthesis_when_created_already_present(
    serializer: CCMMSerializer,
) -> None:
    metadata = {
        "dates": [{"date": "2025-04-27", "type": {"id": "Created"}}],
        "publication_date": "2025-04-27",
    }
    refs = serializer.serialize_time_references(metadata)
    assert len(refs) == 1


def test_serialize_time_references_synthesizes_created_from_publication_date(
    serializer: CCMMSerializer,
) -> None:
    metadata = {
        "dates": [{"date": "2025-04-27", "type": {"id": "Collected"}}],
        "publication_date": "2025-05-01",
    }
    refs = serializer.serialize_time_references(metadata)
    assert len(refs) == 2
    assert "2025-05-01" in xml(refs[1])
    assert "Created" in xml(refs[1])


def test_serialize_time_references_empty(serializer: CCMMSerializer) -> None:
    assert serializer.serialize_time_references({}) == []


# ---------------------------------------------------------------------------
# language_system (from languages[])
# ---------------------------------------------------------------------------


def test_split_languages_first_entry_is_primary(serializer: CCMMSerializer) -> None:
    primary, other = serializer.split_languages([{"id": "CES"}, {"id": "ENG"}])
    assert primary == {"id": "CES"}
    assert other == [{"id": "ENG"}]


def test_split_languages_empty(serializer: CCMMSerializer) -> None:
    assert serializer.split_languages([]) == (None, [])


# ---------------------------------------------------------------------------
# terms_of_use / license (from rights[])
# ---------------------------------------------------------------------------


def test_serialize_terms_of_use_none_when_no_rights(serializer: CCMMSerializer) -> None:
    assert serializer.serialize_terms_of_use({}) is None
    assert serializer.serialize_terms_of_use({"rights": []}) is None


def test_serialize_terms_of_use_with_resolved_license(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    metadata = {"rights": [{"id": "cc-by-4.0", "description": {"en": "A description."}}]}
    el = serializer.serialize_terms_of_use(metadata)
    assert el is not None
    assert el.tag == str(serializer.ns.terms_of_use)
    assert el.find(str(serializer.ns.license)) is not None
    text = xml(el)
    assert "cc-by-4.0" in text
    assert "A description." in text
    # `access_rights` is required by the XSD but has no source field in schema.json --
    # see ccmm_export_plan.md and the docstring of `serialize_terms_of_use`.
    assert_valid_apart_from(schema, el, "access_rights")


def test_serialize_terms_of_use_with_raw_license(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    metadata = {"rights": [{"link": "https://creativecommons.org/licenses/by/4.0/", "title": {"en": "CC BY 4.0"}}]}
    el = serializer.serialize_terms_of_use(metadata)
    assert el is not None
    text = xml(el)
    assert "https://creativecommons.org/licenses/by/4.0/" in text
    assert "CC BY 4.0" in text
    # `access_rights` is required by the XSD but has no source field in schema.json --
    # see ccmm_export_plan.md and the docstring of `serialize_terms_of_use`.
    assert_valid_apart_from(schema, el, "access_rights")


def test_serialize_terms_of_use_uses_only_the_first_right(serializer: CCMMSerializer) -> None:
    metadata = {"rights": [{"id": "first"}, {"id": "second"}]}
    el = serializer.serialize_terms_of_use(metadata)
    assert el is not None
    text = xml(el)
    assert "first" in text
    assert "second" not in text


def test_serialize_license_document_from_raw_right(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    right = {"link": "https://example.org/license", "title": {"en": "Example License", "cs": "Ukázková licence"}}
    el = serializer.serialize_license_document(right)
    assert el.tag == str(serializer.ns.license)
    assert el.findtext(str(serializer.ns.iri)) == "https://example.org/license"
    labels = {(label.get(XML_LANG), label.text) for label in el.findall(str(serializer.ns.label))}
    assert labels == {("en", "Example License"), ("cs", "Ukázková licence")}
    schema.assertValid(as_global_element(el, "license_document"))


# ---------------------------------------------------------------------------
# subject (from subjects[])
# ---------------------------------------------------------------------------


def test_group_subjects_groups_by_id(serializer: CCMMSerializer) -> None:
    metadata = {
        "subjects": [
            {"id": "Frascati:105", "subject": "Env. sciences"},
            {"id": "Frascati:105", "subject": "Vědy o životním prostředí"},
            {"subject": "kvalita ovzduší"},
        ]
    }
    groups = serializer.group_subjects(metadata)
    assert len(groups) == 2
    assert groups[0]["id"] == "Frascati:105"
    assert [item["value"] for item in groups[0]["items"]] == ["Env. sciences", "Vědy o životním prostředí"]
    assert groups[1]["id"] is None
    assert groups[1]["items"] == [{"lang": None, "value": "kvalita ovzduší"}]


def test_group_subjects_empty(serializer: CCMMSerializer) -> None:
    assert serializer.group_subjects({}) == []


def test_serialize_subject_splits_id_into_scheme_and_code(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    group = {"id": "Frascati:105", "items": [{"lang": None, "value": "Environmental sciences"}]}
    el = serializer.serialize_subject(group)
    assert el.tag == str(serializer.ns.subject)
    assert el.findtext(str(serializer.ns.classification_code)) == "105"
    text = xml(el)
    assert "Frascati" in text
    assert "Environmental sciences" in text
    schema.assertValid(el)


def test_serialize_subject_without_id_omits_scheme_and_code(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    group = {"id": None, "items": [{"lang": None, "value": "kvalita ovzduší"}]}
    el = serializer.serialize_subject(group)
    assert el.find(str(serializer.ns.classification_code)) is None
    assert el.find(str(serializer.ns.subject_scheme)) is None
    assert "kvalita ovzduší" in xml(el)
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# location (from locations.features[])
# ---------------------------------------------------------------------------


def test_geojson_to_wkt_point(serializer: CCMMSerializer) -> None:
    assert serializer._geojson_to_wkt({"type": "Point", "coordinates": [1.5, 2.5]}) == "POINT (1.5 2.5)"


def test_geojson_to_wkt_polygon(serializer: CCMMSerializer) -> None:
    geometry = {
        "type": "Polygon",
        "coordinates": [[[13.0, 49.0], [15.0, 49.0], [15.0, 50.0], [13.0, 49.0]]],
    }
    assert serializer._geojson_to_wkt(geometry) == "POLYGON ((13.0 49.0, 15.0 49.0, 15.0 50.0, 13.0 49.0))"


def test_geojson_to_wkt_unknown_type_returns_none(serializer: CCMMSerializer) -> None:
    assert serializer._geojson_to_wkt({"type": "MultiPoint", "coordinates": [[1, 2]]}) is None


def test_geojson_to_wkt_missing_coordinates_returns_none(serializer: CCMMSerializer) -> None:
    assert serializer._geojson_to_wkt({"type": "Point", "coordinates": None}) is None


def test_serialize_geometry_point(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    el = serializer.serialize_geometry({"type": "Point", "coordinates": [1.5, 2.5]})
    assert el.tag == str(serializer.ns.geometry)
    assert el.findtext(str(serializer.ns.wkt)) == "POINT (1.5 2.5)"
    schema.assertValid(el)


def test_serialize_related_object_from_identifier_iri_scheme(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    el = serializer.serialize_related_object_from_identifier({"scheme": "iri", "identifier": "https://example.org/x"})
    assert el.tag == str(serializer.ns.related_object)
    assert el.findtext(str(serializer.ns.iri)) == "https://example.org/x"
    schema.assertValid(as_global_element(el, "related_resource"))


def test_serialize_related_object_from_identifier_other_scheme_falls_back_to_identifier(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    el = serializer.serialize_related_object_from_identifier({"scheme": "doi", "identifier": "10.1234/x"})
    assert el.find(str(serializer.ns.identifier)) is not None
    assert "10.1234/x" in xml(el)
    schema.assertValid(as_global_element(el, "related_resource"))


def test_serialize_location_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    feature = {
        "place": "Středočeský kraj",
        "geometry": {"type": "Point", "coordinates": [14.0, 50.0]},
        "identifiers": [{"scheme": "iri", "identifier": "https://example.org/place"}],
        "description": "BoundingBox",
    }
    el = serializer.serialize_location(feature)
    assert el.tag == str(serializer.ns.location)
    assert el.findtext(str(serializer.ns.name)) == "Středočeský kraj"
    text = xml(el)
    assert "https://example.org/place" in text
    assert "BoundingBox" in text
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# funding_reference (from funding[])
# ---------------------------------------------------------------------------


def test_group_funding_regroups_funders_sharing_the_same_award(serializer: CCMMSerializer) -> None:
    metadata = {
        "funding": [
            {"funder": {"name": "Funder A"}, "award": {"title": {"en": "Award"}, "number": "123"}},
            {"funder": {"name": "Funder B"}, "award": {"title": {"en": "Award"}, "number": "123"}},
            {"funder": {"name": "Funder C"}, "award": {"title": {"en": "Other award"}, "number": "456"}},
        ]
    }
    groups = serializer.group_funding(metadata)
    assert len(groups) == 2
    assert [f["name"] for f in groups[0]["funders"]] == ["Funder A", "Funder B"]
    assert groups[0]["award"]["number"] == "123"
    assert [f["name"] for f in groups[1]["funders"]] == ["Funder C"]


def test_group_funding_empty(serializer: CCMMSerializer) -> None:
    assert serializer.group_funding({}) == []


def test_serialize_funding_reference_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    group = {
        "award": {"title": {"en": "Program for air pollution research"}, "number": "AWARD-1"},
        "funders": [{"name": "Funder A"}, {"name": "Funder B"}],
    }
    el = serializer.serialize_funding_reference(group)
    assert el.tag == str(serializer.ns.funding_reference)
    assert el.findtext(str(serializer.ns.local_identifier)) == "AWARD-1"
    assert el.findtext(str(serializer.ns.award_title)) == "Program for air pollution research"
    # `funder` (type `ccmm:agent`, a choice) wraps `organization`/`person`, the same way
    # `resource_to_agent_relationship/relation` does.
    name_path = f"{serializer.ns.funder}/{serializer.ns.organization}/{serializer.ns.name}"
    assert [name_el.text for name_el in el.findall(name_path)] == ["Funder A", "Funder B"]
    schema.assertValid(el)


def test_serialize_agent_as_organization_delegates_to_serialize_organization(
    serializer: CCMMSerializer,
) -> None:
    funder = {"name": "Funder A"}
    assert xml(serializer.serialize_agent_as_organization(funder)) == xml(serializer.serialize_organization(funder))


# ---------------------------------------------------------------------------
# related_resource (from related_resources[] and related_identifiers[])
# ---------------------------------------------------------------------------


def test_serialize_related_resource_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {
        "title": "Related dataset",
        "identifiers": [{"identifier": "10.1234/related", "scheme": "doi"}],
        "additional_titles": [
            {"title": "Související datová sada", "type": {"id": "TranslatedTitle"}, "lang": {"id": "CES"}}
        ],
        "creators": [{"person_or_org": {"name": "Creator", "type": "personal"}}],
        "dates": [{"date": "2024-01-01", "type": {"id": "Issued"}}],
        "resource_type": {"id": "dataset"},
        "relation_type": {"id": "IsReferencedBy"},
        # Fields with no corresponding `related_resource` XSD slot -- must be dropped,
        # see ccmm_export_plan.md.
        "publisher": "Should be dropped",
        "subjects": [{"subject": "Should be dropped"}],
    }
    el = serializer.serialize_related_resource(entry)
    assert el.tag == str(serializer.ns.related_resource)
    assert el.findtext(str(serializer.ns.title)) == "Related dataset"
    text = xml(el)
    assert "10.1234/related" in text
    assert "Související datová sada" in text
    assert "Creator" in text
    assert "2024-01-01" in text
    assert "Should be dropped" not in text
    schema.assertValid(el)


def test_serialize_related_resource_from_identifier_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {
        "identifier": "https://example.org/x",
        "scheme": "url",
        "relation_type": {"id": "References"},
        "resource_type": {"id": "dataset"},
    }
    el = serializer.serialize_related_resource_from_identifier(entry)
    assert el.tag == str(serializer.ns.related_resource)
    assert "https://example.org/x" in xml(el)
    assert el.find(str(serializer.ns.title)) is None
    schema.assertValid(el)


def test_serialize_related_resources_combines_both_sources_in_order(serializer: CCMMSerializer) -> None:
    metadata = {
        "related_resources": [{"title": "A"}],
        "related_identifiers": [{"identifier": "https://example.org/b"}],
    }
    resources = serializer.serialize_related_resources(metadata)
    assert len(resources) == 2
    assert resources[0].findtext(str(serializer.ns.title)) == "A"
    assert "https://example.org/b" in xml(resources[1])


def test_serialize_related_resources_empty(serializer: CCMMSerializer) -> None:
    assert serializer.serialize_related_resources({}) == []


# ---------------------------------------------------------------------------
# Vocabulary resolution -- serialize_vocabulary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, {}])
def test_serialize_vocabulary_short_circuits_on_falsy_value(
    serializer: CCMMSerializer, value: dict[str, str] | None
) -> None:
    parent = etree.Element("root")
    assert serializer.serialize_vocabulary(parent, serializer.ns.resource_type, "resourcetypes", value) is None
    assert len(parent) == 0


def test_serialize_vocabulary_normalizes_bare_string_id(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    parent = etree.Element("root")
    el = serializer.serialize_vocabulary(parent, serializer.ns.scheme, "identifierschemes", "doi")
    assert el is not None
    assert el.tag == str(serializer.ns.scheme)
    assert el.findtext(str(serializer.ns.iri)) == "https://nma.eosc.cz/vocabularies/identifierschemes/doi"
    schema.assertValid(as_global_element(el, "identifier_scheme"))


def test_serialize_vocabulary_builds_iri_element(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    parent = etree.Element("root")
    el = serializer.serialize_vocabulary(parent, serializer.ns.resource_type, "resourcetypes", {"id": "dataset"})
    assert el is not None
    assert el.tag == str(serializer.ns.resource_type)
    assert el.findtext(str(serializer.ns.iri)) == "https://nma.eosc.cz/vocabularies/resourcetypes/dataset"
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# Section: the dataset root element and the top-level serialize() entrypoint
# ---------------------------------------------------------------------------


def test_serialize_dataset_identification_appends_children_in_xsd_order(
    serializer: CCMMSerializer,
) -> None:
    root = etree.Element(str(serializer.ns.dataset))
    metadata = {
        "identifiers": [{"identifier": "10.1/x", "scheme": "doi"}],
        "version": "1.0",
        "title": "Title",
        "additional_titles": [{"title": "Alt", "type": {"id": "TranslatedTitle"}, "lang": {"id": "en"}}],
        "creators": [{"person_or_org": {"name": "A", "type": "personal"}}],
        "publication_date": "2025-01-01",
    }
    serializer._serialize_dataset_identification(root, metadata)
    tags = [etree.QName(child).localname for child in root]
    assert tags == [
        "identifier",
        "version",
        "title",
        "alternate_title",
        "qualified_relation",
        "publication_year",
        "time_reference",
    ]


def test_serialize_dataset_content_appends_children_in_xsd_order(serializer: CCMMSerializer) -> None:
    root = etree.Element(str(serializer.ns.dataset))
    metadata = {
        "resource_type": {"id": "dataset"},
        "languages": [{"id": "CES"}],
        "rights": [{"id": "cc-by"}],
        "subjects": [{"subject": "x"}],
        "description": "y",
        "locations": {"features": [{"place": "p"}]},
        "funding": [{"funder": {"name": "f"}, "award": {}}],
        "related_resources": [{"title": "r"}],
    }
    serializer._serialize_dataset_content(root, metadata)
    tags = [etree.QName(child).localname for child in root]
    assert tags == [
        "resource_type",
        "primary_language",
        "terms_of_use",
        "subject",
        "description",
        "location",
        "funding_reference",
        "related_resource",
    ]


def test_serialize_accepts_either_full_record_or_bare_metadata(serializer: CCMMSerializer) -> None:
    metadata = {"title": "T"}
    from_bare_metadata = serializer.serialize(metadata)
    from_full_record = serializer.serialize({"id": "abc123", "metadata": metadata})
    assert xml(from_bare_metadata) == xml(from_full_record)


def _minimal_metadata_identification(serializer: CCMMSerializer) -> etree._Element:
    """Build a schema-minimal ``<metadata_identification>``, for the integration test below only.

    ``CCMMXMLProductionParser.parse()`` already strips this field for production
    records (it is reconstructed from Invenio's own technical metadata, not from CCMM
    XML), and ``CCMMSerializer`` deliberately never produces it either -- see
    ccmm_export_plan.md, "Explicitly out of scope". It is nonetheless *required* by the
    XSD's ``dataset`` type, so a full ``<dataset>`` can never be completely schema-valid
    without one. This stand-in exists only so the *rest* of the document's validity can
    be checked below; it is not something ``CCMMSerializer`` is expected to build.
    """
    el = etree.Element(str(serializer.ns.metadata_identification))
    el.append(
        serializer.serialize_resource_to_agent_relationship(
            {"person_or_org": {"name": ":unkn", "type": "personal"}}, {"id": "DataManager"}
        )
    )
    for tag in (serializer.ns.conforms_to_standard, serializer.ns.original_repository):
        placeholder = etree.SubElement(el, str(tag))
        etree.SubElement(placeholder, str(serializer.ns.iri)).text = f"urn:example:{tag.tag}"
    return el


def test_serialize_full_dataset_from_real_example(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    """Integration test: serialize a real production record and check the result.

    Three, already-documented gaps are expected here (everything else
    ``CCMMSerializer`` produces from this record must be schema-valid):

    - ``access_rights`` (required by ``terms_of_use``) and ``metadata_identification``
      (required by ``dataset``) have no source field in schema.json at all -- see
      ccmm_export_plan.md.
    - this record's ``dates[]`` includes a bare-year value (``"2024"``), which is not a
      valid ``xs:date`` -- see the docstring of ``serialize_time_reference_from_date``.
    - this record's one location has no ``description``, the only (already-documented,
      best-effort) source ``serialize_location`` has for the otherwise-required
      ``relation_type`` -- see its docstring.
    """
    with (DATA_DIR / "2026-01-29_example.json").open(encoding="utf-8") as f:
        record = json.load(f)

    dataset_el = serializer.serialize(record)
    assert dataset_el.tag == str(serializer.ns.dataset)

    text = xml(dataset_el)
    assert "Kvalita ovzduší ve středních čechách 2024" in text
    assert "10.45321/as36sl" in text
    assert "Novák, Jan" in text
    assert "Univerzita Karlova" in text
    assert "Grantová agentura České republiky" in text
    assert "Long-term trends of PM2.5" in text

    bare_year_date_gap = "is not a valid value of the atomic type 'xs:date'"
    missing_location_relation_type_gap = f"{{{CCMM_NS}}}location': Missing"
    known_gaps = (
        "metadata_identification",
        "access_rights",
        bare_year_date_gap,
        missing_location_relation_type_gap,
    )
    assert_valid_apart_from(schema, dataset_el, *known_gaps)

    # With a stand-in for the one always-missing required field, the rest must validate.
    dataset_el.insert(0, _minimal_metadata_identification(serializer))
    assert_valid_apart_from(schema, dataset_el, "access_rights", bare_year_date_gap, missing_location_relation_type_gap)

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

Every test that produces one or more ``lxml`` elements:

1. builds them from a small, valid, hand-written JSON fragment (matching ``schema.json``),
2. asserts the *whole* canonicalized (C14N 2.0) XML matches a literal expected string --
   see ``c14n`` -- rather than picking the result apart with several ``find``/``get``
   calls; the expected string is written as readable, indented, pretty-printed XML and
   flattened back to one line with ``join_xml``, and
3. validates the element against the real CCMM XSD (see ``as_global_element`` and
   ``tests/data/xsd/README.md`` for how a fragment -- as opposed to a whole document --
   gets validated in isolation).

``CCMMSerializer.serialize_vocabulary`` resolves every vocabulary type through the same
placeholder NMA IRI scheme for now (``https://nma.eosc.cz/vocabularies/{type}/{id}``) --
real, per-type resolution is expected to replace it later. That is exactly why tests
exercise the real ``CCMMSerializer`` directly rather than a fake: the placeholder already
gives deterministic, checkable output.
"""

# ruff: noqa: SLF001, RUF001, E501 -- SLF001: this file deliberately tests private helpers
# too (per its brief: "meticulously add tests for each of the created methods, starting
# with the leaf ones"). RUF001/E501: the big pretty-printed XML fixture in
# test_serialize_full_dataset_from_real_example contains real record content (en dashes,
# long running text/coordinate lists) that `join_xml` reassembles by stripping each
# line -- reflowing or "fixing" characters inside it would corrupt the fixture, and a
# per-line suppression comment on an inner line of a triple-quoted string would become
# part of the string itself.

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from invenio_rdm_records.records.api import RDMRecord
from lxml import etree

from ccmm_invenio.serializers.production.ccmm import CCMMSerializer

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


def c14n(element: etree._Element) -> str:
    """Canonicalize `element` (C14N 2.0) into a deterministic string for exact-match assertions.

    Canonicalization assigns namespace prefixes deterministically (``ns0``, ``ns1``, ...)
    regardless of how the tree was built and drops insignificant whitespace, so the result
    is stable to compare literally against a hand-written expected string -- a single
    assertion against the whole element instead of several separate ``find``/``get`` checks.
    """
    return etree.tostring(element, method="c14n2", strip_text=True).decode()


def join_xml(xml: str) -> str:
    """Join an indented, triple-quoted, multi-line XML literal back into one line.

    Lets expected-XML literals in this file be written as readable, pretty-printed
    XML (one element per line, indented by nesting depth) while still comparing
    against ``c14n()``'s single-line output: splits on newlines and strips each line
    (leading/trailing whitespace only -- no text content in these fixtures spans a
    line break).
    """
    return "".join(line.strip() for line in xml.splitlines())


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
    serializer._append_text(parent, serializer.ns.title, "hello")
    assert c14n(parent) == join_xml(
        """
        <root>
          <ns0:title xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">hello</ns0:title>
        </root>
        """
    )


@pytest.mark.parametrize("value", [None, ""])
def test_append_text_does_nothing_for_falsy_value(serializer: CCMMSerializer, value: str | None) -> None:
    parent = etree.Element("root")
    assert serializer._append_text(parent, serializer.ns.title, value) is None
    assert len(parent) == 0


def test_append_i18n_text_sets_xml_lang(serializer: CCMMSerializer) -> None:
    parent = etree.Element("root")
    serializer._append_i18n_text(parent, serializer.ns.title, "cs", "Ahoj")
    assert c14n(parent) == join_xml(
        """
        <root>
          <ns0:title xmlns:ns0="https://schema.ccmm.cz/research-data/1.1" xml:lang="cs">Ahoj</ns0:title>
        </root>
        """
    )


def test_append_i18n_text_defaults_missing_lang_to_und(serializer: CCMMSerializer) -> None:
    parent = etree.Element("root")
    serializer._append_i18n_text(parent, serializer.ns.title, None, "Ahoj")
    assert c14n(parent) == join_xml(
        """
        <root>
          <ns0:title xmlns:ns0="https://schema.ccmm.cz/research-data/1.1" xml:lang="und">Ahoj</ns0:title>
        </root>
        """
    )


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
    assert c14n(el) == join_xml(
        """
        <ns0:identifier xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:value>10.1234/abc</ns0:value>
          <ns0:scheme>
            <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/doi</ns0:iri>
          </ns0:scheme>
        </ns0:identifier>
        """
    )
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
    assert c14n(el) == join_xml(
        """
        <ns0:alternate_title xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:title xml:lang="en">Air quality in 2024</ns0:title>
          <ns0:title xml:lang="cs">Kvalita ovzduší 2024</ns0:title>
          <ns0:alternate_title_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/titletypes/TranslatedTitle</ns0:iri>
          </ns0:alternate_title_type>
        </ns0:alternate_title>
        """
    )
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# description (from the single "description" field and from additional_descriptions[])
# ---------------------------------------------------------------------------


def test_serialize_description_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    group = {"type": {"id": "abstract"}, "items": [{"lang": "CES", "value": "Popis datové sady."}]}
    el = serializer.serialize_description(group)
    assert c14n(el) == join_xml(
        """
        <ns0:description xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:description_text xml:lang="CES">Popis datové sady.</ns0:description_text>
          <ns0:description_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/descriptiontypes/abstract</ns0:iri>
          </ns0:description_type>
        </ns0:description>
        """
    )
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
    assert c14n(el) == join_xml(
        """
        <ns0:organization xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:identifier>
            <ns0:value>12345</ns0:value>
            <ns0:scheme>
              <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/ror</ns0:iri>
            </ns0:scheme>
          </ns0:identifier>
          <ns0:name>Univerzita Karlova</ns0:name>
        </ns0:organization>
        """
    )
    schema.assertValid(el)


def test_serialize_person_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    person = {
        "name": "Novák, Jan",
        "given_name": "Jan",
        "family_name": "Novák",
        "identifiers": [{"identifier": "0000-0003-0852-6632", "scheme": "orcid"}],
    }
    el = serializer.serialize_person(person, affiliations=[{"name": "Univerzita Karlova"}])
    assert c14n(el) == join_xml(
        """
        <ns0:person xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:identifier>
            <ns0:value>0000-0003-0852-6632</ns0:value>
            <ns0:scheme>
              <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/orcid</ns0:iri>
            </ns0:scheme>
          </ns0:identifier>
          <ns0:name>Novák, Jan</ns0:name>
          <ns0:given_name>Jan</ns0:given_name>
          <ns0:family_name>Novák</ns0:family_name>
          <ns0:affiliation>
            <ns0:name>Univerzita Karlova</ns0:name>
          </ns0:affiliation>
        </ns0:person>
        """
    )
    schema.assertValid(el)


def test_serialize_person_splits_multi_word_given_and_family_names(serializer: CCMMSerializer) -> None:
    person = {"name": "x", "given_name": "Jan Maria", "family_name": "Novák Svoboda"}
    el = serializer.serialize_person(person)
    assert c14n(el) == join_xml(
        """
        <ns0:person xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:name>x</ns0:name>
          <ns0:given_name>Jan</ns0:given_name>
          <ns0:given_name>Maria</ns0:given_name>
          <ns0:family_name>Novák</ns0:family_name>
          <ns0:family_name>Svoboda</ns0:family_name>
        </ns0:person>
        """
    )


def test_serialize_resource_to_agent_relationship_person(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {
        "person_or_org": {"name": "Novák, Jan", "type": "personal", "given_name": "Jan", "family_name": "Novák"},
        "affiliations": [{"name": "Univerzita Karlova"}],
    }
    el = serializer.serialize_resource_to_agent_relationship(entry, {"id": "Creator"})
    assert c14n(el) == join_xml(
        """
        <ns0:qualified_relation xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:relation>
            <ns0:person>
              <ns0:name>Novák, Jan</ns0:name>
              <ns0:given_name>Jan</ns0:given_name>
              <ns0:family_name>Novák</ns0:family_name>
              <ns0:affiliation>
                <ns0:name>Univerzita Karlova</ns0:name>
              </ns0:affiliation>
            </ns0:person>
          </ns0:relation>
          <ns0:role>
            <ns0:iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/Creator</ns0:iri>
          </ns0:role>
        </ns0:qualified_relation>
        """
    )
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
    # `Should be dropped` (the affiliation) is absent -- confirmed by the exact match below.
    assert c14n(el) == join_xml(
        """
        <ns0:qualified_relation xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:relation>
            <ns0:organization>
              <ns0:name>Czech Hydrometeorological Institute</ns0:name>
            </ns0:organization>
          </ns0:relation>
          <ns0:role>
            <ns0:iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/DataCollector</ns0:iri>
          </ns0:role>
        </ns0:qualified_relation>
        """
    )
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
    # defaulted role for the creator, since no explicit "role" was given for it above.
    assert [c14n(relation) for relation in relations] == [
        join_xml(
            """
            <ns0:qualified_relation xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
              <ns0:relation>
                <ns0:person>
                  <ns0:name>Creator One</ns0:name>
                </ns0:person>
              </ns0:relation>
              <ns0:role>
                <ns0:iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/Creator</ns0:iri>
              </ns0:role>
            </ns0:qualified_relation>
            """
        ),
        join_xml(
            """
            <ns0:qualified_relation xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
              <ns0:relation>
                <ns0:person>
                  <ns0:name>Contributor One</ns0:name>
                </ns0:person>
              </ns0:relation>
              <ns0:role>
                <ns0:iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/DataCollector</ns0:iri>
              </ns0:role>
            </ns0:qualified_relation>
            """
        ),
    ]
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
    assert c14n(el) == join_xml(
        """
        <ns0:time_reference xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:temporal_representation>
            <ns0:time_instant>
              <ns0:date>2025-04-27</ns0:date>
            </ns0:time_instant>
          </ns0:temporal_representation>
          <ns0:date_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/datetypes/Collected</ns0:iri>
          </ns0:date_type>
          <ns0:date_information xml:lang="und">Date collected</ns0:date_information>
        </ns0:time_reference>
        """
    )
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
    assert [c14n(ref) for ref in refs] == [
        join_xml(
            """
            <ns0:time_reference xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
              <ns0:temporal_representation>
                <ns0:time_instant>
                  <ns0:date>2025-04-27</ns0:date>
                </ns0:time_instant>
              </ns0:temporal_representation>
              <ns0:date_type>
                <ns0:iri>https://nma.eosc.cz/vocabularies/datetypes/Collected</ns0:iri>
              </ns0:date_type>
            </ns0:time_reference>
            """
        ),
        join_xml(
            """
            <ns0:time_reference xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
              <ns0:temporal_representation>
                <ns0:time_instant>
                  <ns0:date>2025-05-01</ns0:date>
                </ns0:time_instant>
              </ns0:temporal_representation>
              <ns0:date_type>
                <ns0:iri>https://nma.eosc.cz/vocabularies/datetypes/Created</ns0:iri>
              </ns0:date_type>
            </ns0:time_reference>
            """
        ),
    ]


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
    assert c14n(el) == join_xml(
        """
        <ns0:terms_of_use xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:license>
            <ns0:iri>https://nma.eosc.cz/vocabularies/licenses/cc-by-4.0</ns0:iri>
          </ns0:license>
          <ns0:description xml:lang="en">A description.</ns0:description>
        </ns0:terms_of_use>
        """
    )
    # `access_rights` is required by the XSD but has no source field in schema.json --
    # see ccmm_export_plan.md and the docstring of `serialize_terms_of_use`.
    assert_valid_apart_from(schema, el, "access_rights")


def test_serialize_terms_of_use_with_raw_license(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    metadata = {"rights": [{"link": "https://creativecommons.org/licenses/by/4.0/", "title": {"en": "CC BY 4.0"}}]}
    el = serializer.serialize_terms_of_use(metadata)
    assert el is not None
    assert c14n(el) == join_xml(
        """
        <ns0:terms_of_use xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:license>
            <ns0:iri>https://creativecommons.org/licenses/by/4.0/</ns0:iri>
            <ns0:label xml:lang="en">CC BY 4.0</ns0:label>
          </ns0:license>
        </ns0:terms_of_use>
        """
    )
    # `access_rights` is required by the XSD but has no source field in schema.json --
    # see ccmm_export_plan.md and the docstring of `serialize_terms_of_use`.
    assert_valid_apart_from(schema, el, "access_rights")


def test_serialize_terms_of_use_uses_only_the_first_right(serializer: CCMMSerializer) -> None:
    metadata = {"rights": [{"id": "first"}, {"id": "second"}]}
    el = serializer.serialize_terms_of_use(metadata)
    assert el is not None
    # "second" is entirely absent -- confirmed by the exact match below.
    assert c14n(el) == join_xml(
        """
        <ns0:terms_of_use xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:license>
            <ns0:iri>https://nma.eosc.cz/vocabularies/licenses/first</ns0:iri>
          </ns0:license>
        </ns0:terms_of_use>
        """
    )


def test_serialize_terms_of_use_with_access_rights(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    # Unlike the tests above, an explicit `access_rights` (as `serialize()` passes down
    # from `access_rights_from_record`, see below) resolves `terms_of_use/access_rights`.
    metadata = {"rights": [{"id": "cc-by-4.0"}]}
    el = serializer.serialize_terms_of_use(metadata, access_rights={"id": "c_abf2"})
    assert el is not None
    assert c14n(el) == join_xml(
        """
        <ns0:terms_of_use xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:access_rights>
            <ns0:iri>https://nma.eosc.cz/vocabularies/accessrights/c_abf2</ns0:iri>
          </ns0:access_rights>
          <ns0:license>
            <ns0:iri>https://nma.eosc.cz/vocabularies/licenses/cc-by-4.0</ns0:iri>
          </ns0:license>
        </ns0:terms_of_use>
        """
    )
    schema.assertValid(el)


def test_serialize_license_document_from_raw_right(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    right = {"link": "https://example.org/license", "title": {"en": "Example License", "cs": "Ukázková licence"}}
    el = serializer.serialize_license_document(right)
    assert c14n(el) == join_xml(
        """
        <ns0:license xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:iri>https://example.org/license</ns0:iri>
          <ns0:label xml:lang="en">Example License</ns0:label>
          <ns0:label xml:lang="cs">Ukázková licence</ns0:label>
        </ns0:license>
        """
    )
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
    assert c14n(el) == join_xml(
        """
        <ns0:subject xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:title xml:lang="und">Environmental sciences</ns0:title>
          <ns0:classification_code>105</ns0:classification_code>
          <ns0:subject_scheme>
            <ns0:iri>https://nma.eosc.cz/vocabularies/subjectschemes/Frascati</ns0:iri>
          </ns0:subject_scheme>
        </ns0:subject>
        """
    )
    schema.assertValid(el)


def test_serialize_subject_without_id_omits_scheme_and_code(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    group = {"id": None, "items": [{"lang": None, "value": "kvalita ovzduší"}]}
    el = serializer.serialize_subject(group)
    assert c14n(el) == join_xml(
        """
        <ns0:subject xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:title xml:lang="und">kvalita ovzduší</ns0:title>
        </ns0:subject>
        """
    )
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
    assert c14n(el) == join_xml(
        """
        <ns0:geometry xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:wkt>POINT (1.5 2.5)</ns0:wkt>
        </ns0:geometry>
        """
    )
    schema.assertValid(el)


def test_serialize_related_object_from_identifier_iri_scheme(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    el = serializer.serialize_related_object_from_identifier({"scheme": "iri", "identifier": "https://example.org/x"})
    assert c14n(el) == join_xml(
        """
        <ns0:related_object xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:iri>https://example.org/x</ns0:iri>
        </ns0:related_object>
        """
    )
    schema.assertValid(as_global_element(el, "related_resource"))


def test_serialize_related_object_from_identifier_other_scheme_falls_back_to_identifier(
    serializer: CCMMSerializer, schema: etree.XMLSchema
) -> None:
    el = serializer.serialize_related_object_from_identifier({"scheme": "doi", "identifier": "10.1234/x"})
    assert c14n(el) == join_xml(
        """
        <ns0:related_object xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:identifier>
            <ns0:value>10.1234/x</ns0:value>
            <ns0:scheme>
              <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/doi</ns0:iri>
            </ns0:scheme>
          </ns0:identifier>
        </ns0:related_object>
        """
    )
    schema.assertValid(as_global_element(el, "related_resource"))


def test_serialize_location_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    feature = {
        "place": "Středočeský kraj",
        "geometry": {"type": "Point", "coordinates": [14.0, 50.0]},
        "identifiers": [{"scheme": "iri", "identifier": "https://example.org/place"}],
        "description": "BoundingBox",
    }
    el = serializer.serialize_location(feature)
    assert c14n(el) == join_xml(
        """
        <ns0:location xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:name>Středočeský kraj</ns0:name>
          <ns0:geometry>
            <ns0:wkt>POINT (14.0 50.0)</ns0:wkt>
          </ns0:geometry>
          <ns0:related_object>
            <ns0:iri>https://example.org/place</ns0:iri>
          </ns0:related_object>
          <ns0:relation_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/locationrelationtypes/BoundingBox</ns0:iri>
          </ns0:relation_type>
        </ns0:location>
        """
    )
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
    # `funder` (type `ccmm:agent`, a choice) wraps `organization`/`person`, the same way
    # `resource_to_agent_relationship/relation` does.
    assert c14n(el) == join_xml(
        """
        <ns0:funding_reference xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:local_identifier>AWARD-1</ns0:local_identifier>
          <ns0:award_title>Program for air pollution research</ns0:award_title>
          <ns0:funder>
            <ns0:organization>
              <ns0:name>Funder A</ns0:name>
            </ns0:organization>
          </ns0:funder>
          <ns0:funder>
            <ns0:organization>
              <ns0:name>Funder B</ns0:name>
            </ns0:organization>
          </ns0:funder>
        </ns0:funding_reference>
        """
    )
    schema.assertValid(el)


def test_serialize_agent_as_organization_delegates_to_serialize_organization(
    serializer: CCMMSerializer,
) -> None:
    funder = {"name": "Funder A"}
    assert c14n(serializer.serialize_agent_as_organization(funder)) == c14n(serializer.serialize_organization(funder))


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
    # "Should be dropped" (publisher/subjects) is entirely absent -- confirmed by the exact match below.
    assert c14n(el) == join_xml(
        """
        <ns0:related_resource xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:identifier>
            <ns0:value>10.1234/related</ns0:value>
            <ns0:scheme>
              <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/doi</ns0:iri>
            </ns0:scheme>
          </ns0:identifier>
          <ns0:title>Related dataset</ns0:title>
          <ns0:alternate_title>
            <ns0:title xml:lang="cs">Související datová sada</ns0:title>
            <ns0:alternate_title_type>
              <ns0:iri>https://nma.eosc.cz/vocabularies/titletypes/TranslatedTitle</ns0:iri>
            </ns0:alternate_title_type>
          </ns0:alternate_title>
          <ns0:qualified_relation>
            <ns0:relation>
              <ns0:person>
                <ns0:name>Creator</ns0:name>
              </ns0:person>
            </ns0:relation>
            <ns0:role>
              <ns0:iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/Creator</ns0:iri>
            </ns0:role>
          </ns0:qualified_relation>
          <ns0:time_reference>
            <ns0:temporal_representation>
              <ns0:time_instant>
                <ns0:date>2024-01-01</ns0:date>
              </ns0:time_instant>
            </ns0:temporal_representation>
            <ns0:date_type>
              <ns0:iri>https://nma.eosc.cz/vocabularies/datetypes/Issued</ns0:iri>
            </ns0:date_type>
          </ns0:time_reference>
          <ns0:resource_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/resourcetypes/dataset</ns0:iri>
          </ns0:resource_type>
          <ns0:resource_relation_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/IsReferencedBy</ns0:iri>
          </ns0:resource_relation_type>
        </ns0:related_resource>
        """
    )
    schema.assertValid(el)


def test_serialize_related_resource_from_identifier_valid(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    entry = {
        "identifier": "https://example.org/x",
        "scheme": "url",
        "relation_type": {"id": "References"},
        "resource_type": {"id": "dataset"},
    }
    el = serializer.serialize_related_resource_from_identifier(entry)
    # No `title` -- confirmed by the exact match below.
    assert c14n(el) == join_xml(
        """
        <ns0:related_resource xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:identifier>
            <ns0:value>https://example.org/x</ns0:value>
            <ns0:scheme>
              <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/url</ns0:iri>
            </ns0:scheme>
          </ns0:identifier>
          <ns0:resource_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/resourcetypes/dataset</ns0:iri>
          </ns0:resource_type>
          <ns0:resource_relation_type>
            <ns0:iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/References</ns0:iri>
          </ns0:resource_relation_type>
        </ns0:related_resource>
        """
    )
    schema.assertValid(el)


def test_serialize_related_resources_combines_both_sources_in_order(serializer: CCMMSerializer) -> None:
    metadata = {
        "related_resources": [{"title": "A"}],
        "related_identifiers": [{"identifier": "https://example.org/b"}],
    }
    resources = serializer.serialize_related_resources(metadata)
    assert [c14n(resource) for resource in resources] == [
        join_xml(
            """
            <ns0:related_resource xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
              <ns0:title>A</ns0:title>
            </ns0:related_resource>
            """
        ),
        join_xml(
            """
            <ns0:related_resource xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
              <ns0:identifier>
                <ns0:value>https://example.org/b</ns0:value>
              </ns0:identifier>
            </ns0:related_resource>
            """
        ),
    ]


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
    assert c14n(el) == join_xml(
        """
        <ns0:scheme xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:iri>https://nma.eosc.cz/vocabularies/identifierschemes/doi</ns0:iri>
        </ns0:scheme>
        """
    )
    schema.assertValid(as_global_element(el, "identifier_scheme"))


def test_serialize_vocabulary_builds_iri_element(serializer: CCMMSerializer, schema: etree.XMLSchema) -> None:
    parent = etree.Element("root")
    el = serializer.serialize_vocabulary(parent, serializer.ns.resource_type, "resourcetypes", {"id": "dataset"})
    assert el is not None
    assert c14n(el) == join_xml(
        """
        <ns0:resource_type xmlns:ns0="https://schema.ccmm.cz/research-data/1.1">
          <ns0:iri>https://nma.eosc.cz/vocabularies/resourcetypes/dataset</ns0:iri>
        </ns0:resource_type>
        """
    )
    schema.assertValid(el)


# ---------------------------------------------------------------------------
# access_rights_from_record (from record.access.status, which lives outside metadata)
# ---------------------------------------------------------------------------


def test_access_status_to_access_rights_mapping_covers_every_access_status(serializer: CCMMSerializer) -> None:
    from invenio_rdm_records.records.systemfields.access.field.record import AccessStatusEnum

    assert {status.value for status in AccessStatusEnum} == set(serializer.ACCESS_STATUS_TO_ACCESS_RIGHTS)


def test_access_rights_from_record_reads_the_records_computed_access_status(
    app,
    db,
    identity_simple,
    search_clear,
    location,
    vocab_fixtures,
    serializer: CCMMSerializer,
) -> None:
    """Check that `access_rights_from_record` reads a real record's computed access status.

    `record.access.status` needs a *real* record: it depends on the record's ``files``
    system field too (see ``RecordAccess.status``), which a record built by hand (e.g.
    plain ``RDMRecord({...})``) does not reliably have wired up. Going through the
    actual service, the same way ``tests/test_production_repository.py`` does, is the
    only way to get a genuinely representative record for this.
    """
    from oarepo_runtime.typing import record_from_result

    from tests.model import production_dataset

    service = production_dataset.proxies.current_service
    result = service.create(
        identity_simple,
        data={
            "access": {"record": "restricted", "files": "restricted"},
            "metadata": {
                "title": "test",
                "publication_date": "2022-01-01",
                "resource_type": {"id": "dataset"},
                "creators": [{"person_or_org": {"type": "personal", "given_name": "John", "family_name": "Doe"}}],
            },
        },
    )
    record = record_from_result(result)
    assert record.access.status.value == "restricted"
    assert serializer.access_rights_from_record(record) == {"id": "c_16ec"}


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


def test_serialize_takes_metadata_from_the_full_record(serializer: CCMMSerializer) -> None:
    metadata = {"title": "T"}
    record = RDMRecord({"id": "abc123", "metadata": metadata})
    assert c14n(serializer.serialize(record)) == c14n(serializer.serialize_dataset(metadata))


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

    - ``metadata_identification`` (required by ``dataset``) has no source field in
      schema.json at all -- see ccmm_export_plan.md.
    - this record's ``dates[]`` includes a bare-year value (``"2024"``), which is not a
      valid ``xs:date`` -- see the docstring of ``serialize_time_reference_from_date``.
    - this record's one location has no ``description``, the only (already-documented,
      best-effort) source ``serialize_location`` has for the otherwise-required
      ``relation_type`` -- see its docstring.

    ``terms_of_use/access_rights`` is *not* a gap here: this fixture record has no
    ``access``/``files`` data of its own, so ``record.access.status`` falls back to
    Invenio's own default (``metadata-only``), which ``serialize()`` still resolves via
    ``access_rights_from_record`` -- see the assertion below.
    """
    with (DATA_DIR / "2026-01-29_example.json").open(encoding="utf-8") as f:
        record = RDMRecord(json.load(f))
    assert record.access.status.value == "metadata-only"

    dataset_el = serializer.serialize(record)
    assert c14n(dataset_el) == join_xml(
        """
        <dataset xmlns="https://schema.ccmm.cz/research-data/1.1">
          <identifier>
            <value>10.45321/as36sl</value>
            <scheme>
              <iri>https://nma.eosc.cz/vocabularies/identifierschemes/doi</iri>
            </scheme>
          </identifier>
          <version>1.0.23</version>
          <title>Kvalita ovzduší ve středních čechách 2024</title>
          <alternate_title>
            <title xml:lang="en">Air quality measurements in Central Bohemian Region in 2024.</title>
            <alternate_title_type>
              <iri>https://nma.eosc.cz/vocabularies/titletypes/TranslatedTitle</iri>
            </alternate_title_type>
          </alternate_title>
          <qualified_relation>
            <relation>
              <person>
                <name>Novák, Jan</name>
                <given_name>Jan</given_name>
                <family_name>Novák</family_name>
                <affiliation>
                  <name>Univerzita Karlova</name>
                </affiliation>
              </person>
            </relation>
            <role>
              <iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/Other</iri>
            </role>
          </qualified_relation>
          <publication_year>2025</publication_year>
          <time_reference>
            <temporal_representation>
              <time_instant>
                <date>2025-04-27</date>
              </time_instant>
            </temporal_representation>
            <date_type>
              <iri>https://nma.eosc.cz/vocabularies/datetypes/Collected</iri>
            </date_type>
            <date_information xml:lang="und">Date collected</date_information>
          </time_reference>
          <time_reference>
            <temporal_representation>
              <time_instant>
                <date>2024</date>
              </time_instant>
            </temporal_representation>
            <date_type>
              <iri>https://nma.eosc.cz/vocabularies/datetypes/Collected</iri>
            </date_type>
            <date_information xml:lang="und">Collection period</date_information>
          </time_reference>
          <time_reference>
            <temporal_representation>
              <time_instant>
                <date>2025</date>
              </time_instant>
            </temporal_representation>
            <date_type>
              <iri>https://nma.eosc.cz/vocabularies/datetypes/Created</iri>
            </date_type>
          </time_reference>
          <resource_type>
            <iri>https://nma.eosc.cz/vocabularies/resourcetypes/c_ddb1</iri>
          </resource_type>
          <primary_language>
            <iri>https://nma.eosc.cz/vocabularies/languages/CES</iri>
          </primary_language>
          <other_language>
            <iri>https://nma.eosc.cz/vocabularies/languages/ENG</iri>
          </other_language>
          <terms_of_use>
            <access_rights>
              <iri>https://nma.eosc.cz/vocabularies/accessrights/c_14cb</iri>
            </access_rights>
            <license>
              <iri>https://customlicense.org/licenses/by/4.0/</iri>
              <label xml:lang="en">A custom license</label>
            </license>
            <description xml:lang="en">A description.</description>
          </terms_of_use>
          <subject>
            <title xml:lang="und">Meteorologie, vědy o atmosféře</title>
          </subject>
          <subject>
            <title xml:lang="und">kvalita ovzduší</title>
          </subject>
          <subject>
            <title xml:lang="und">Environmental monitoring facilities</title>
          </subject>
          <description>
            <description_text xml:lang="cs">Tato datová sada obsahuje měření kvality ovzduší ve středních Čechách v roce 2024.</description_text>
            <description_type>
              <iri>https://nma.eosc.cz/vocabularies/descriptiontypes/abstract</iri>
            </description_type>
          </description>
          <location>
            <name>Středočeský kraj</name>
            <geometry>
              <wkt>POLYGON ((13.394972 49.50127, 15.585575 49.50127, 15.585575 50.614216, 13.394972 50.614216, 13.394972 49.50127))</wkt>
            </geometry>
          </location>
          <funding_reference>
            <local_identifier>https://doi.org/award-identifier</local_identifier>
            <award_title>Program for air pollution research</award_title>
            <funder>
              <organization>
                <name>Grantová agentura České republiky</name>
              </organization>
            </funder>
          </funding_reference>
          <related_resource>
            <identifier>
              <value>10.56789/ias.pm25.2025.001</value>
              <scheme>
                <iri>https://nma.eosc.cz/vocabularies/identifierschemes/doi</iri>
              </scheme>
            </identifier>
            <title>Long-term trends of PM2.5 concentrations in the Central Bohemian Region (2010–2024)</title>
            <alternate_title>
              <title xml:lang="cs">Dlouhodobé trendy koncentrací PM2.5 ve Středočeském kraji (2010–2024)</title>
              <alternate_title_type>
                <iri>https://nma.eosc.cz/vocabularies/titletypes/TranslatedTitle</iri>
              </alternate_title_type>
            </alternate_title>
            <qualified_relation>
              <relation>
                <person>
                  <name>Svobodová, Petra</name>
                  <given_name>Petra</given_name>
                  <family_name>Svobodová</family_name>
                  <affiliation>
                    <name>Institute of Atmospheric Studies, Prague</name>
                  </affiliation>
                </person>
              </relation>
              <role>
                <iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/Creator</iri>
              </role>
            </qualified_relation>
            <qualified_relation>
              <relation>
                <person>
                  <name>Müller, Thomas</name>
                  <given_name>Thomas</given_name>
                  <family_name>Müller</family_name>
                  <affiliation>
                    <name>Charles University</name>
                  </affiliation>
                </person>
              </relation>
              <role>
                <iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/Creator</iri>
              </role>
            </qualified_relation>
            <qualified_relation>
              <relation>
                <organization>
                  <name>Czech Hydrometeorological Institute</name>
                </organization>
              </relation>
              <role>
                <iri>https://nma.eosc.cz/vocabularies/resourceagentroletypes/DataCollector</iri>
              </role>
            </qualified_relation>
            <resource_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcetypes/c_2df8fbb1</iri>
            </resource_type>
            <resource_relation_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/IsReferencedBy</iri>
            </resource_relation_type>
          </related_resource>
          <related_resource>
            <identifier>
              <value>http://data.europa.eu/eli/dir/2008/50/oj</value>
              <scheme>
                <iri>https://nma.eosc.cz/vocabularies/identifierschemes/url</iri>
              </scheme>
            </identifier>
            <resource_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcetypes/c_18cf</iri>
            </resource_type>
            <resource_relation_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/IsReferencedBy</iri>
            </resource_relation_type>
          </related_resource>
          <related_resource>
            <identifier>
              <value>https://www.envitech-bohemia.cz/p/264/envi-lvs1-sampler-pro-odber-prasneho-aerosolu</value>
              <scheme>
                <iri>https://nma.eosc.cz/vocabularies/identifierschemes/url</iri>
              </scheme>
            </identifier>
            <resource_relation_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/References</iri>
            </resource_relation_type>
          </related_resource>
          <related_resource>
            <identifier>
              <value>https://opendata.chmi.cz/air_quality/now/data/</value>
              <scheme>
                <iri>https://nma.eosc.cz/vocabularies/identifierschemes/url</iri>
              </scheme>
            </identifier>
            <resource_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcetypes/c_ddb1</iri>
            </resource_type>
            <resource_relation_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/IsDerivedFrom</iri>
            </resource_relation_type>
          </related_resource>
          <related_resource>
            <identifier>
              <value>https://data.gov.cz/zdroj/datové-sady/00020699/c724d055011d82189bbfc3766ffd1eb7</value>
              <scheme>
                <iri>https://nma.eosc.cz/vocabularies/identifierschemes/url</iri>
              </scheme>
            </identifier>
            <resource_relation_type>
              <iri>https://nma.eosc.cz/vocabularies/resourcerelationtypes/HasMetadata</iri>
            </resource_relation_type>
          </related_resource>
        </dataset>
        """
    )

    bare_year_date_gap = "is not a valid value of the atomic type 'xs:date'"
    missing_location_relation_type_gap = f"{{{CCMM_NS}}}location': Missing"
    known_gaps = ("metadata_identification", bare_year_date_gap, missing_location_relation_type_gap)
    assert_valid_apart_from(schema, dataset_el, *known_gaps)

    # With a stand-in for the one always-missing required field, the rest must validate.
    dataset_el.insert(0, _minimal_metadata_identification(serializer))
    assert_valid_apart_from(schema, dataset_el, bare_year_date_gap, missing_location_relation_type_gap)

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from rdflib import RDF, RDFS, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    DATACITE_TITLE_TYPE_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    CCMMTitleTypesReader,
    RDMTitleTypesReader,
    TitleTypesMerger,
)
from ccmm_invenio.fixtures.compiler.readers.skosmos import SkosmosReader

CCMM = "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/"


def test_load_title_types():
    reader = RDMTitleTypesReader("uri:does_not_matter")
    title_types = reader.read()

    assert isinstance(title_types, Graph)

    vocab = make_vocabulary_namespace("titletypes")

    # the well-known alternative-title type, carrying its DataCite titleType
    alternative_title = vocab["alternative-title"]
    assert (alternative_title, RDF.type, SKOS.Concept) in title_types
    assert (alternative_title, SKOS.inScheme, URIRef(vocab)) in title_types
    assert [
        str(n) for n in title_types.objects(alternative_title, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE
    ] == ["alternative-title"]
    assert (alternative_title, SKOS.prefLabel, Literal("Alternative title", lang="en")) in title_types
    assert (alternative_title, SKOS.prefLabel, Literal("Alternativní název", lang="cs")) in title_types

    assert (alternative_title, PROPS_NAMESPACE.datacite, Literal("AlternativeTitle")) in title_types

    # the concept is matched to the DataCite titleType it maps to
    assert (
        alternative_title,
        SKOS.exactMatch,
        DATACITE_TITLE_TYPE_NAMESPACE["AlternativeTitle"],
    ) in title_types
    assert (
        vocab["subtitle"],
        SKOS.exactMatch,
        DATACITE_TITLE_TYPE_NAMESPACE["Subtitle"],
    ) in title_types

    # the vocabulary is flat: every entry is a top concept
    concepts = set(title_types.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(title_types.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(title_types.triples((None, SKOS.broader, None)))
    assert len(concepts) == 4

    # the prop is declared in the graph itself
    assert (PROPS_NAMESPACE.datacite, RDF.type, RDF.Property) in title_types
    assert (PROPS_NAMESPACE.datacite, RDFS.comment, None) in title_types


def make_ccmm_source_graph():
    """Return a mocked CCMM AlternateTitle codelist with four title types."""
    source = Graph()
    source.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in (
        ("AlternativeTitle", "Alternative Title", "Alternativní název"),
        ("Subtitle", "Subtitle", "Podnázev"),
        ("TranslatedTitle", "Translated Title", "Přeložený název"),
        ("Other", "Other", "Jiný"),
    ):
        ccmm_uri = URIRef(CCMM + name)
        source.add((URIRef(CCMM), SKOS.hasTopConcept, ccmm_uri))
        source.add((ccmm_uri, RDF.type, SKOS.Concept))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(en, lang="en")))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(cs, lang="cs")))
    return source


def test_ccmm_title_types(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    reader = CCMMTitleTypesReader(CCMM)
    graph = reader.read()

    vocab = make_vocabulary_namespace("titletypes")

    # the CamelCase CCMM names become the kebab-case RDM ids
    alternative_title = vocab["alternative-title"]
    assert (alternative_title, RDF.type, SKOS.Concept) in graph
    assert (alternative_title, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(alternative_title, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "alternative-title"
    ]

    # linked to the CCMM authority, labels kept with their languages
    assert (alternative_title, SKOS.exactMatch, URIRef(CCMM + "AlternativeTitle")) in graph
    assert (alternative_title, SKOS.prefLabel, Literal("Alternative Title", lang="en")) in graph
    assert (alternative_title, SKOS.prefLabel, Literal("Alternativní název", lang="cs")) in graph

    # the other concepts round out the same four title types
    assert {str(c).rsplit("/", 1)[-1] for c in graph.subjects(RDF.type, SKOS.Concept)} == {
        "alternative-title",
        "subtitle",
        "translated-title",
        "other",
    }


def test_title_types_merger(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    rdm = RDMTitleTypesReader().read()
    ccmm = CCMMTitleTypesReader(CCMM).read()
    merged = TitleTypesMerger(ccmm, rdm).merge()

    vocab = make_vocabulary_namespace("titletypes")
    alternative_title = vocab["alternative-title"]

    # the CCMM labels are single-valued per language - they replace the RDM
    # ones, so there is exactly one prefLabel per language
    assert (alternative_title, SKOS.prefLabel, Literal("Alternative Title", lang="en")) in merged
    assert (alternative_title, SKOS.prefLabel, Literal("Alternativní název", lang="cs")) in merged
    assert (alternative_title, SKOS.prefLabel, Literal("Alternative title", lang="en")) not in merged

    # both authority links are present, the props survive the merge
    assert (alternative_title, SKOS.exactMatch, DATACITE_TITLE_TYPE_NAMESPACE["AlternativeTitle"]) in merged
    assert (alternative_title, SKOS.exactMatch, URIRef(CCMM + "AlternativeTitle")) in merged
    assert (alternative_title, PROPS_NAMESPACE.datacite, Literal("AlternativeTitle")) in merged

    # the id notation is not duplicated
    assert len(list(merged.objects(alternative_title, SKOS.notation))) == 1


def test_title_types_merger_add_missing(monkeypatch):
    def make_source_with_extra() -> Graph:
        source = make_ccmm_source_graph()
        main_title = URIRef(CCMM + "MainTitle")
        source.add((URIRef(CCMM), SKOS.hasTopConcept, main_title))
        source.add((main_title, RDF.type, SKOS.Concept))
        source.add((main_title, SKOS.prefLabel, Literal("Main Title", lang="en")))
        source.add((main_title, SKOS.prefLabel, Literal("Hlavní název", lang="cs")))
        return source

    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_source_with_extra())

    rdm = RDMTitleTypesReader().read()
    ccmm = CCMMTitleTypesReader(CCMM).read()

    # concepts without an RDM counterpart are skipped by default
    merged = TitleTypesMerger(ccmm, rdm).merge()
    main_title = make_vocabulary_namespace("titletypes")["main-title"]
    assert (main_title, None, None) not in merged

    # ... and created complete with add_missing=True
    merged = TitleTypesMerger(ccmm, rdm).merge(add_missing=True)
    assert (main_title, RDF.type, SKOS.Concept) in merged
    assert [str(n) for n in merged.objects(main_title, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "main-title"
    ]
    assert (main_title, SKOS.prefLabel, Literal("Main Title", lang="en")) in merged
    assert (main_title, SKOS.prefLabel, Literal("Hlavní název", lang="cs")) in merged
    assert (main_title, SKOS.exactMatch, URIRef(CCMM + "MainTitle")) in merged

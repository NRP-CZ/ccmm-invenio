#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from rdflib import RDF, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    CCMMRelationTypeReader,
    DataciteReader,
    DataciteRelationTypeReader,
    RelationTypesMerger,
)
from ccmm_invenio.fixtures.compiler.readers.skosmos import SkosmosReader

SCHEME_URI = "https://w3id.org/tib/datacite/vocab/relationType"
TIB = "https://w3id.org/tib/datacite/vocab/relationType/"
CCMM = "https://vocabs.ccmm.cz/registry/codelist/RelationType/"


def make_datacite_source_graph():
    """Return a mocked DataCite distribution with two relation types."""
    source = Graph()
    source.add((URIRef(SCHEME_URI), RDF.type, SKOS.ConceptScheme))
    for name in ("IsCitedBy", "Other"):
        tib_uri = URIRef(TIB + name)
        source.add((URIRef(SCHEME_URI), SKOS.hasTopConcept, tib_uri))
        source.add((tib_uri, RDF.type, SKOS.Concept))
        source.add((tib_uri, SKOS.prefLabel, Literal(name, lang="en")))
        source.add((tib_uri, SKOS.definition, Literal(f"indicates {name}", lang="en")))
        source.add((tib_uri, SKOS.inScheme, URIRef(SCHEME_URI)))
    return source


def test_datacite_relation_types(monkeypatch):
    def fail_parse(self, source: str, **kwargs: object) -> None:
        raise AssertionError("the source graph must be injected, not fetched")

    monkeypatch.setattr(Graph, "parse", fail_parse)

    reader = DataciteRelationTypeReader(make_datacite_source_graph, SCHEME_URI)
    graph = reader.read()

    relation_types = make_vocabulary_namespace("relationtypes")
    is_cited_by = relation_types["iscitedby"]

    assert (is_cited_by, RDF.type, SKOS.Concept) in graph
    assert (is_cited_by, SKOS.inScheme, URIRef(relation_types)) in graph
    assert (URIRef(relation_types), SKOS.hasTopConcept, is_cited_by) in graph

    # the id is the lowercase DataCite name
    assert (
        is_cited_by,
        SKOS.notation,
        Literal("iscitedby", datatype=NOTATION_ID_DATATYPE),
    ) in graph

    # the prop carries the exact DataCite name
    assert (is_cited_by, PROPS_NAMESPACE.datacite, Literal("IsCitedBy")) in graph

    # linked to the TIB authority and carrying its labels
    assert (is_cited_by, SKOS.exactMatch, URIRef(TIB + "IsCitedBy")) in graph
    assert (is_cited_by, SKOS.prefLabel, Literal("IsCitedBy", lang="en")) in graph
    assert (is_cited_by, SKOS.definition, Literal("indicates IsCitedBy", lang="en")) in graph

    other = relation_types["other"]
    assert (other, SKOS.notation, Literal("other", datatype=NOTATION_ID_DATATYPE)) in graph
    assert (other, PROPS_NAMESPACE.datacite, Literal("Other")) in graph


def test_datacite_reader(monkeypatch):
    def fake_parse(self, source: str, **kwargs: object) -> Graph:
        assert source == "https://example.org/datacite.rdf"
        assert kwargs.get("format") == "xml"
        self.add((URIRef(TIB + "IsCitedBy"), RDF.type, SKOS.Concept))
        return self

    monkeypatch.setattr(Graph, "parse", fake_parse)

    graph = DataciteReader("https://example.org/datacite.rdf").read()

    assert (URIRef(TIB + "IsCitedBy"), RDF.type, SKOS.Concept) in graph


def test_ccmm_relation_types(monkeypatch):
    source = Graph()
    source.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in (
        ("IsTranslationOf", "is translation of", "je překladem (čeho)"),
        ("Other", "other", "jiný"),
    ):
        ccmm_uri = URIRef(CCMM + name)
        source.add((URIRef(CCMM), SKOS.hasTopConcept, ccmm_uri))
        source.add((ccmm_uri, RDF.type, SKOS.Concept))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(en, lang="en")))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(cs, lang="cs")))

    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: source)

    reader = CCMMRelationTypeReader(CCMM)
    graph = reader.read()

    relation_types = make_vocabulary_namespace("relationtypes")
    is_translation_of = relation_types["istranslationof"]

    assert (is_translation_of, RDF.type, SKOS.Concept) in graph
    assert (is_translation_of, SKOS.inScheme, URIRef(relation_types)) in graph

    # the id is the lowercase CCMM name
    assert (
        is_translation_of,
        SKOS.notation,
        Literal("istranslationof", datatype=NOTATION_ID_DATATYPE),
    ) in graph

    # linked to the CCMM authority, labels kept with their languages
    assert (is_translation_of, SKOS.exactMatch, URIRef(CCMM + "IsTranslationOf")) in graph
    assert (is_translation_of, SKOS.prefLabel, Literal("is translation of", lang="en")) in graph
    assert (is_translation_of, SKOS.prefLabel, Literal("je překladem (čeho)", lang="cs")) in graph

    # the datacite prop is reserved for the DataCite vocabulary
    assert (is_translation_of, PROPS_NAMESPACE.datacite, None) not in graph


def make_datacite_and_ccmm_graphs(monkeypatch):
    """Return (datacite, ccmm) relation type graphs with mocked sources."""
    datacite = DataciteRelationTypeReader(make_datacite_source_graph, SCHEME_URI).read()

    ccmm_source = Graph()
    ccmm_source.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in (
        ("IsTranslationOf", "is translation of", "je překladem (čeho)"),
        ("Other", "other", "jiný"),
    ):
        ccmm_uri = URIRef(CCMM + name)
        ccmm_source.add((URIRef(CCMM), SKOS.hasTopConcept, ccmm_uri))
        ccmm_source.add((ccmm_uri, RDF.type, SKOS.Concept))
        ccmm_source.add((ccmm_uri, SKOS.prefLabel, Literal(en, lang="en")))
        ccmm_source.add((ccmm_uri, SKOS.prefLabel, Literal(cs, lang="cs")))
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: ccmm_source)
    ccmm = CCMMRelationTypeReader(CCMM).read()

    return datacite, ccmm


def test_relation_types_merger(monkeypatch):
    datacite, ccmm = make_datacite_and_ccmm_graphs(monkeypatch)
    merged = RelationTypesMerger(ccmm, datacite).merge()

    relation_types = make_vocabulary_namespace("relationtypes")
    other = relation_types["other"]

    # the CCMM labels are single-valued per language - they replace the
    # DataCite ones, so there is exactly one prefLabel per language
    assert (other, SKOS.prefLabel, Literal("other", lang="en")) in merged
    assert (other, SKOS.prefLabel, Literal("jiný", lang="cs")) in merged
    assert (other, SKOS.prefLabel, Literal("Other", lang="en")) not in merged

    # both authority links are present
    assert (other, SKOS.exactMatch, URIRef(TIB + "Other")) in merged
    assert (other, SKOS.exactMatch, URIRef(CCMM + "Other")) in merged

    # the id notation is not duplicated
    assert len(list(merged.objects(other, SKOS.notation))) == 1

    # concepts without a DataCite counterpart are skipped by default
    is_translation_of = relation_types["istranslationof"]
    assert (is_translation_of, None, None) not in merged


def test_relation_types_merger_add_missing(monkeypatch):
    datacite, ccmm = make_datacite_and_ccmm_graphs(monkeypatch)
    merged = RelationTypesMerger(ccmm, datacite).merge(add_missing=True)

    relation_types = make_vocabulary_namespace("relationtypes")
    is_translation_of = relation_types["istranslationof"]

    # the CCMM-only concept is created complete
    assert (is_translation_of, RDF.type, SKOS.Concept) in merged
    assert (is_translation_of, SKOS.inScheme, URIRef(relation_types)) in merged
    assert (
        is_translation_of,
        SKOS.notation,
        Literal("istranslationof", datatype=NOTATION_ID_DATATYPE),
    ) in merged
    assert (is_translation_of, SKOS.prefLabel, Literal("is translation of", lang="en")) in merged
    assert (is_translation_of, SKOS.prefLabel, Literal("je překladem (čeho)", lang="cs")) in merged
    assert (is_translation_of, SKOS.exactMatch, URIRef(CCMM + "IsTranslationOf")) in merged

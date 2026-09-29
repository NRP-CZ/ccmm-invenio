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
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import CCMMLocationRelationsReader
from ccmm_invenio.fixtures.compiler.readers.skosmos import SkosmosReader

CCMM = "https://vocabs.ccmm.cz/registry/codelist/LocationRelation/"


def make_ccmm_source_graph():
    """Return a mocked CCMM LocationRelation codelist with its five concepts."""
    source = Graph()
    source.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in (
        ("Stored", "Stored at location", "Uchováno v lokaci"),
        ("Refers", "Refers to the location", "Týká se lokace"),
        ("Processed", "Processed at location", "Zpracováno v lokaci"),
        ("Collected", "Collected in", "Získáno v lokaci"),
        ("Other", "Other", "Jiné"),
    ):
        ccmm_uri = URIRef(CCMM + name)
        source.add((URIRef(CCMM), SKOS.hasTopConcept, ccmm_uri))
        source.add((ccmm_uri, RDF.type, SKOS.Concept))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(en, lang="en")))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(cs, lang="cs")))
    return source


def test_ccmm_location_relations(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    reader = CCMMLocationRelationsReader(CCMM)
    graph = reader.read()

    vocab = make_vocabulary_namespace("locationrelations")

    # the CCMM names are lowercased into the vocabulary entry ids
    stored = vocab["stored"]
    assert (stored, RDF.type, SKOS.Concept) in graph
    assert (stored, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(stored, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["stored"]

    # linked to the CCMM authority, labels kept with their languages
    assert (stored, SKOS.exactMatch, URIRef(CCMM + "Stored")) in graph
    assert (stored, SKOS.prefLabel, Literal("Stored at location", lang="en")) in graph
    assert (stored, SKOS.prefLabel, Literal("Uchováno v lokaci", lang="cs")) in graph

    # the vocabulary is flat: every entry is a top concept
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(graph.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(graph.triples((None, SKOS.broader, None)))
    assert {str(c).rsplit("/", 1)[-1] for c in concepts} == {
        "stored",
        "refers",
        "processed",
        "collected",
        "other",
    }

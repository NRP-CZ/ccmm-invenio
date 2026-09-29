#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests of the identifier schemes vocabulary and its curated fragment."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from rdflib import RDF, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    NOTATION_ID_DATATYPE,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    CuratedVocabularyReader,
    IdentifiersMerger,
    RDMIdentifierSchemesReader,
)

DATA_DIR = Path(files("ccmm_invenio.fixtures.input.vocabularies"))


def merged_identifier_schemes() -> Graph:
    """Return the RDM identifier schemes merged with the curated fragment."""
    return IdentifiersMerger(
        CuratedVocabularyReader(DATA_DIR / "identifierschemes.ttl", "identifierschemes").read(),
        RDMIdentifierSchemesReader("uri:does_not_matter").read(),
    ).merge(add_missing=True)


def test_rdm_identifier_schemes():
    graph = RDMIdentifierSchemesReader("uri:does_not_matter").read()

    assert isinstance(graph, Graph)

    vocab = make_vocabulary_namespace("identifierschemes")

    # a config scheme, carrying its id notation, label and tag
    orcid = vocab["orcid"]
    assert (orcid, RDF.type, SKOS.Concept) in graph
    assert (orcid, SKOS.prefLabel, Literal("ORCID", lang="en")) in graph
    assert (orcid, TAGS_URI, Literal("person-organization")) in graph

    # the curated fragment concepts are not among them
    assert (vocab["ares"], RDF.type, SKOS.Concept) not in graph


def test_curated_identifier_schemes():
    graph = merged_identifier_schemes()

    vocab = make_vocabulary_namespace("identifierschemes")

    # the fragment concepts were created, carrying their id notations,
    # labels, tags and the resolver IRIs CCMM identifies them by
    ares = vocab["ares"]
    assert (ares, RDF.type, SKOS.Concept) in graph
    assert [str(n) for n in graph.objects(ares, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["ares"]
    assert (ares, SKOS.prefLabel, Literal("ARES", lang="en")) in graph
    assert (ares, SKOS.definition, Literal("Administrative Register of Economic Subjects", lang="en")) in graph
    assert (ares, SKOS.exactMatch, URIRef("https://ares.gov.cz/")) in graph
    assert (ares, TAGS_URI, Literal("person-organization")) in graph

    for scheme, iri in (
        ("iri", "urn:iri"),
        ("researcherid", "https://www.webofscience.com/"),
        ("scopusid", "https://www.scopus.com/"),
    ):
        concept = vocab[scheme]
        assert (concept, RDF.type, SKOS.Concept) in graph
        assert (concept, SKOS.exactMatch, URIRef(iri)) in graph

    # the RDM config schemes survived the merge untouched
    assert (vocab["orcid"], RDF.type, SKOS.Concept) in graph

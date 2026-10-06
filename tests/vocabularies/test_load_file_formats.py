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
    EUVOC_NAMESPACE,
    NOTATION_ID_DATATYPE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import EUFileFormatsReader
from ccmm_invenio.fixtures.compiler.readers.file_formats import OP_MAPPED_CODE

EU = "http://publications.europa.eu/resource/authority/file-type/"

DEPRECATED = URIRef("http://publications.europa.eu/ontology/authority/deprecated")


def make_eu_source_graph():
    """Return a mocked EU file type table with three concepts."""
    source = Graph()
    source.add((URIRef(EU), RDF.type, SKOS.ConceptScheme))

    pdf = URIRef(EU + "PDF")
    source.add((pdf, RDF.type, SKOS.Concept))
    source.add((pdf, SKOS.inScheme, URIRef(EU)))
    source.add((pdf, SKOS.topConceptOf, URIRef(EU)))
    source.add((pdf, SKOS.prefLabel, Literal("PDF", lang="en")))
    source.add((pdf, SKOS.prefLabel, Literal("PDF", lang="et")))
    source.add((pdf, SKOS.altLabel, Literal("Portable Document Format", lang="en")))
    source.add(
        (
            pdf,
            SKOS.definition,
            Literal(
                "PDF - Portable Document Format - is a file format developed "
                "to present documents independent of application software.",
                lang="en",
            ),
        )
    )
    source.add((pdf, SKOS.notation, Literal("application/pdf", datatype=EUVOC_NAMESPACE.IANA_MT)))
    source.add((pdf, SKOS.notation, Literal(".pdf", datatype=EUVOC_NAMESPACE.FILE_EXT)))
    source.add((pdf, DEPRECATED, Literal("false")))
    source.add((pdf, SKOS.historyNote, Literal("ISO 32000-1", lang="en")))

    # the mapped-code link whose blank node would dangle after the re-homing
    source.add((pdf, OP_MAPPED_CODE, Literal("mapped")))

    sevenzip = URIRef(EU + "7Z")
    source.add((sevenzip, RDF.type, SKOS.Concept))
    source.add((sevenzip, SKOS.inScheme, URIRef(EU)))
    source.add((sevenzip, SKOS.topConceptOf, URIRef(EU)))
    source.add((sevenzip, SKOS.prefLabel, Literal("7Z", lang="en")))
    source.add((sevenzip, SKOS.altLabel, Literal("7-Zip compressed file", lang="en")))
    source.add((sevenzip, DEPRECATED, Literal("true")))

    return source


def test_eu_file_formats(monkeypatch):
    monkeypatch.setattr(EUFileFormatsReader, "fetch_source", lambda _self: make_eu_source_graph())

    reader = EUFileFormatsReader()
    graph = reader.read()

    vocab = make_vocabulary_namespace("fileformats")

    # the authority codes are lowercased into the vocabulary entry ids
    pdf = vocab["pdf"]
    assert (pdf, RDF.type, SKOS.Concept) in graph
    assert (pdf, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(pdf, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["pdf"]

    # linked to the authority, labels and definitions kept with their
    # languages - in the supported label languages only
    assert (pdf, SKOS.exactMatch, URIRef(EU + "PDF")) in graph
    assert (pdf, SKOS.prefLabel, Literal("PDF", lang="en")) in graph
    assert (pdf, SKOS.prefLabel, Literal("PDF", lang="et")) not in graph
    assert (pdf, SKOS.altLabel, Literal("Portable Document Format", lang="en")) in graph
    assert (pdf, DEPRECATED, Literal("false")) in graph
    assert (pdf, SKOS.historyNote, Literal("ISO 32000-1", lang="en")) in graph

    # the typed euvoc notations coexist with the id notation
    notations = graph.objects(pdf, SKOS.notation)
    assert (pdf, SKOS.notation, Literal("application/pdf", datatype=EUVOC_NAMESPACE.IANA_MT)) in graph
    assert (pdf, SKOS.notation, Literal(".pdf", datatype=EUVOC_NAMESPACE.FILE_EXT)) in graph
    assert len(list(notations)) == 3

    # the mapped-code links are dropped
    assert not list(graph.triples((None, OP_MAPPED_CODE, None)))

    # the vocabulary is flat: every entry is a top concept
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(graph.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert {str(c).rsplit("/", 1)[-1] for c in concepts} == {"pdf", "7z"}

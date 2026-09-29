#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    NOTATION_ID_DATATYPE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    SPDXChecksumAlgorithmsReader,
)
from ccmm_invenio.fixtures.compiler.readers.checksum_algorithms import (
    SPDX_NAMESPACE,
    TERM_STATUS,
)

SPDX = "http://spdx.org/rdf/terms#"


def make_spdx_source_graph():
    """Return a mocked SPDX 2.3 ontology with four checksum algorithms."""
    source = Graph()
    for name, comment in (
        ("checksumAlgorithm_blake2b256", "Indicates the algorithm used was BLAKE2b-256."),
        ("checksumAlgorithm_md5", "Indicates the algorithm used was MD5"),
        ("checksumAlgorithm_sha3_512", "Indicates the algorithm used was SHA3-512."),
        ("checksumAlgorithm_adler32", "Indicates the algorithm used was ADLER32."),
    ):
        individual = URIRef(SPDX + name)
        source.add((individual, RDF.type, SPDX_NAMESPACE.ChecksumAlgorithm))
        source.add((individual, RDF.type, OWL.NamedIndividual))
        source.add((individual, RDFS.comment, Literal(comment, lang="en")))
        source.add((individual, TERM_STATUS, Literal("stable", lang="en")))
    return source


def test_spdx_checksum_algorithms(monkeypatch):
    monkeypatch.setattr(SPDXChecksumAlgorithmsReader, "fetch_source", lambda _self: make_spdx_source_graph())

    reader = SPDXChecksumAlgorithmsReader()
    graph = reader.read()

    vocab = make_vocabulary_namespace("checksumalgorithms")

    # the checksumAlgorithm_ prefix is dropped from the SPDX names
    blake2b256 = vocab["blake2b256"]
    assert (blake2b256, RDF.type, SKOS.Concept) in graph
    assert (blake2b256, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(blake2b256, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "blake2b256"
    ]

    # linked to the SPDX individual; the algorithm name is lifted out of the
    # comment as the prefLabel, the comment itself becomes the definition
    assert (blake2b256, SKOS.exactMatch, URIRef(SPDX + "checksumAlgorithm_blake2b256")) in graph
    assert (blake2b256, SKOS.prefLabel, Literal("BLAKE2b-256", lang="en")) in graph
    assert (
        blake2b256,
        SKOS.definition,
        Literal("Indicates the algorithm used was BLAKE2b-256.", lang="en"),
    ) in graph

    # also without the trailing period, and with the underscored sha3 name
    md5 = vocab["md5"]
    assert (md5, SKOS.prefLabel, Literal("MD5", lang="en")) in graph
    sha3_512 = vocab["sha3_512"]
    assert (sha3_512, SKOS.prefLabel, Literal("SHA3-512", lang="en")) in graph

    # the term_status note is an editorial detail and is dropped
    assert not list(graph.triples((None, TERM_STATUS, None)))

    # the vocabulary is flat: every entry is a top concept
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(graph.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert {str(c).rsplit("/", 1)[-1] for c in concepts} == {
        "blake2b256",
        "md5",
        "sha3_512",
        "adler32",
    }

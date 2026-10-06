#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

import yaml
from rdflib import RDF, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    NOTATION_ID_DATATYPE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.invenio_export import export_subjects
from ccmm_invenio.fixtures.compiler.readers import SUBJECT_SCHEME, SubjectsReader

CCMM = "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/"

# the OECD FORD fields of the mocked codelist: two major fields, a field
# nesting below the first one and the FORD code nesting below it (the URIs
# nest the codes as well, the way the CCMM registry serves them), each
# mapped to its English and Czech labels and the path of its parent
CONCEPTS = {
    "10000": ("Natural sciences", "Přírodní vědy", None),
    "10000/10100": ("Mathematics", "Matematika", "10000"),
    "10000/10100/10101": ("Pure mathematics", "Čistá matematika", "10000/10100"),
    "20000": ("Engineering and technology", "Technické vědy, inženýrství", None),
}


def make_ccmm_source_graphs():
    """Mock the Skosmos data endpoint responses of the SubjectCategory codelist.

    The codelist URI serves the scheme and the top concepts only; each
    concept serves its own details with the stubs of the concepts nesting
    below it, the way the Skosmos data endpoint does.
    """
    scheme = Graph()
    scheme.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for path, (en, cs, parent_path) in CONCEPTS.items():
        if parent_path is not None:
            continue
        top = URIRef(CCMM + path)
        scheme.add((URIRef(CCMM), SKOS.hasTopConcept, top))
        scheme.add((top, RDF.type, SKOS.Concept))
        scheme.add((top, SKOS.prefLabel, Literal(en, lang="en")))
        scheme.add((top, SKOS.prefLabel, Literal(cs, lang="cs")))

    graphs = {CCMM: scheme}
    for path, (en, cs, parent_path) in CONCEPTS.items():
        concept = URIRef(CCMM + path)
        graph = Graph()
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.inScheme, URIRef(CCMM)))
        graph.add((concept, SKOS.prefLabel, Literal(en, lang="en")))
        graph.add((concept, SKOS.prefLabel, Literal(cs, lang="cs")))
        graph.add((concept, SKOS.definition, Literal(f"The FORD field {en}.", lang="en")))
        if parent_path is None:
            graph.add((concept, SKOS.topConceptOf, URIRef(CCMM)))
        else:
            graph.add((concept, SKOS.broader, URIRef(CCMM + parent_path)))
        # the stubs of the narrower concepts nesting below
        for child_path, (child_en, child_cs, child_parent_path) in CONCEPTS.items():
            if child_parent_path != path:
                continue
            child = URIRef(CCMM + child_path)
            graph.add((child, RDF.type, SKOS.Concept))
            graph.add((child, SKOS.prefLabel, Literal(child_en, lang="en")))
            graph.add((child, SKOS.prefLabel, Literal(child_cs, lang="cs")))
            graph.add((child, SKOS.broader, concept))
        graphs[str(concept)] = graph
    return graphs


def patch_subject_category(monkeypatch):
    """Serve the mocked SubjectCategory data endpoint responses to the reader."""
    graphs = make_ccmm_source_graphs()
    monkeypatch.setattr(SubjectsReader, "fetch_graph", lambda _self, url: graphs[url])
    monkeypatch.setattr(
        SubjectsReader,
        "data_url",
        lambda self, uri=None: self.uri if uri is None else uri,
    )


def test_data_url():
    reader = SubjectsReader(CCMM)

    # the vocabulary id is the segment after "codelist" - also for the
    # concept URIs nesting the codes below it
    assert reader.data_url() == (
        "https://vocabs.ccmm.cz/rest/v1/SubjectCategory/data"
        "?uri=https%3A%2F%2Fvocabs.ccmm.cz%2Fregistry%2Fcodelist%2FSubjectCategory%2F"
        "&format=text/turtle"
    )
    assert reader.data_url(CCMM + "10000/10100/10101") == (
        "https://vocabs.ccmm.cz/rest/v1/SubjectCategory/data"
        "?uri=https%3A%2F%2Fvocabs.ccmm.cz%2Fregistry%2Fcodelist%2FSubjectCategory"
        "%2F10000%2F10100%2F10101&format=text/turtle"
    )


def test_subjects(monkeypatch):
    patch_subject_category(monkeypatch)

    graph = SubjectsReader(CCMM).read()

    vocab = make_vocabulary_namespace("subjects")

    # the nested concept was fetched individually - its definition, served
    # only by its own data, is present; its id is the scheme-prefixed
    # classification code
    pure = vocab["ford:10101"]
    assert (pure, RDF.type, SKOS.Concept) in graph
    assert (pure, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(pure, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["ford:10101"]
    assert (pure, SKOS.definition, Literal("The FORD field Pure mathematics.", lang="en")) in graph

    # linked to the CCMM authority, labels kept with their languages
    assert (pure, SKOS.exactMatch, URIRef(CCMM + "10000/10100/10101")) in graph
    assert (pure, SKOS.prefLabel, Literal("Pure mathematics", lang="en")) in graph
    assert (pure, SKOS.prefLabel, Literal("Čistá matematika", lang="cs")) in graph

    # the hierarchy is rebuilt between the re-homed concepts - the source
    # broader links point at the CCMM concepts, the graph carries its own
    assert (pure, SKOS.broader, vocab["ford:10100"]) in graph
    assert (vocab["ford:10100"], SKOS.narrower, pure) in graph
    assert (vocab["ford:10100"], SKOS.broader, vocab["ford:10000"]) in graph

    # the concepts without a re-homed parent are the top concepts
    top = {str(concept)[len(str(vocab)) :] for concept in graph.subjects(SKOS.topConceptOf, URIRef(vocab))}
    assert top == {"ford:10000", "ford:20000"}
    assert len(set(graph.subjects(RDF.type, SKOS.Concept))) == len(CONCEPTS)


def test_export_subjects(monkeypatch, tmp_path):
    """The subjects graph exports into the fixture the subjects service reads."""
    patch_subject_category(monkeypatch)

    graph = SubjectsReader(CCMM).read()

    output_path = tmp_path / "subjects.yaml"
    export_subjects(graph, output_path, SUBJECT_SCHEME)
    entries = {entry["id"]: entry for entry in yaml.safe_load(output_path.read_text())}

    assert set(entries) == {"ford:10000", "ford:10100", "ford:10101", "ford:20000"}

    # the entry carries the fields the subjects schema of invenio knows:
    # the scheme-prefixed classification code as the id, the scheme, the
    # English label as the subject and the prefLabels as the title
    pure = entries["ford:10101"]
    assert pure["scheme"] == "FORD"
    assert pure["subject"] == "Pure mathematics"
    assert pure["title"] == {"cs": "Čistá matematika", "en": "Pure mathematics"}

    # the hierarchy is carried by the parents prop, single level: the id
    # of the parent concept
    # the FORD code is carried by the classification_code prop
    assert pure["props"] == {"classification_code": "10101", "parents": "ford:10100"}
    assert entries["ford:10100"]["props"] == {"classification_code": "10100", "parents": "ford:10000"}
    assert entries["ford:10000"]["props"] == {"classification_code": "10000"}

    # the authority link is carried as the URL identifier
    assert pure["identifiers"] == [
        {
            "scheme": "url",
            "identifier": "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/10000/10100/10101",
        }
    ]

    # the fields the subjects schema does not know are dropped
    assert "description" not in pure
    assert "synonyms" not in pure

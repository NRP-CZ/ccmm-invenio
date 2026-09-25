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
    DATACITE_DATE_TYPE_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    CCMMDateTypesReader,
    DateTypesMerger,
    RDMDateTypesReader,
)
from ccmm_invenio.fixtures.compiler.readers.skosmos import SkosmosReader

CCMM = "https://vocabs.ccmm.cz/registry/codelist/TimeReference/"


def test_load_date_types():
    reader = RDMDateTypesReader("uri:does_not_matter")
    date_types = reader.read()

    assert isinstance(date_types, Graph)

    vocab = make_vocabulary_namespace("datetypes")

    # the well-known collected date type, carrying its DataCite dateType
    collected = vocab["collected"]
    assert (collected, RDF.type, SKOS.Concept) in date_types
    assert (collected, SKOS.inScheme, URIRef(vocab)) in date_types
    assert [str(n) for n in date_types.objects(collected, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "collected"
    ]
    assert (collected, SKOS.prefLabel, Literal("Collected", lang="en")) in date_types
    assert (collected, SKOS.prefLabel, Literal("Sebrané", lang="cs")) in date_types

    assert (collected, PROPS_NAMESPACE.datacite, Literal("Collected")) in date_types

    # the concept is matched to the DataCite dateType it maps to
    assert (
        collected,
        SKOS.exactMatch,
        DATACITE_DATE_TYPE_NAMESPACE["Collected"],
    ) in date_types
    assert (
        vocab["copyrighted"],
        SKOS.exactMatch,
        DATACITE_DATE_TYPE_NAMESPACE["Copyrighted"],
    ) in date_types

    # the vocabulary is flat: every entry is a top concept
    concepts = set(date_types.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(date_types.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(date_types.triples((None, SKOS.broader, None)))
    assert len(concepts) == 12

    # the prop is declared in the graph itself
    assert (PROPS_NAMESPACE.datacite, RDF.type, RDF.Property) in date_types
    assert (PROPS_NAMESPACE.datacite, RDFS.comment, None) in date_types


def make_ccmm_source_graph():
    """Return a mocked CCMM TimeReference codelist with the twelve date types."""
    source = Graph()
    source.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in (
        ("Accepted", "Date Accepted", "Datum přijetí"),
        ("Available", "Date Available", "Datum zveřejnění"),
        ("Collected", "Date Collected", "Datum sběru"),
        ("Copyrighted", "Date Copyrighted", "Datum udělení copyrightu"),
        ("Created", "Date Created", "Datum vytvoření"),
        ("Issued", "Date Issued", "Datum vydání"),
        ("Other", "Other date", "Jiné datum"),
        ("Submitted", "Date Submitted", "Datum podání"),
        ("Updated", "Date Updated", "Datum aktualizace"),
        ("Valid", "Date Valid", "Datum platnosti"),
        ("Withdrawn", "Date Withdrawn", "Datum odstranění"),
        ("Coverage", "Date Coverage", "Časové pokrytí"),
    ):
        ccmm_uri = URIRef(CCMM + name)
        source.add((URIRef(CCMM), SKOS.hasTopConcept, ccmm_uri))
        source.add((ccmm_uri, RDF.type, SKOS.Concept))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(en, lang="en")))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(cs, lang="cs")))
    return source


def test_ccmm_date_types(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    reader = CCMMDateTypesReader(CCMM)
    graph = reader.read()

    vocab = make_vocabulary_namespace("datetypes")

    # the CamelCase CCMM names become the kebab-case RDM ids
    collected = vocab["collected"]
    assert (collected, RDF.type, SKOS.Concept) in graph
    assert (collected, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(collected, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "collected"
    ]

    # linked to the CCMM authority, labels kept with their languages
    assert (collected, SKOS.exactMatch, URIRef(CCMM + "Collected")) in graph
    assert (collected, SKOS.prefLabel, Literal("Date Collected", lang="en")) in graph
    assert (collected, SKOS.prefLabel, Literal("Datum sběru", lang="cs")) in graph

    # the other concepts round out the same twelve date types
    assert {str(c).rsplit("/", 1)[-1] for c in graph.subjects(RDF.type, SKOS.Concept)} == {
        "accepted",
        "available",
        "collected",
        "copyrighted",
        "created",
        "issued",
        "other",
        "submitted",
        "updated",
        "valid",
        "withdrawn",
        "coverage",
    }


def test_date_types_merger(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    rdm = RDMDateTypesReader().read()
    ccmm = CCMMDateTypesReader(CCMM).read()
    merged = DateTypesMerger(ccmm, rdm).merge()

    vocab = make_vocabulary_namespace("datetypes")
    collected = vocab["collected"]

    # the CCMM labels are single-valued per language - they replace the RDM
    # ones, so there is exactly one prefLabel per language; the CCMM labels
    # carry the shared "Date" qualifier, so they win for English too
    assert (collected, SKOS.prefLabel, Literal("Date Collected", lang="en")) in merged
    assert (collected, SKOS.prefLabel, Literal("Datum sběru", lang="cs")) in merged
    assert (collected, SKOS.prefLabel, Literal("Collected", lang="en")) not in merged
    assert (collected, SKOS.prefLabel, Literal("Sebrané", lang="cs")) not in merged

    # the labels of unsupported languages are discarded when reading, so they
    # do not reach the merge at all
    assert (collected, SKOS.prefLabel, Literal("Gesammelt", lang="de")) not in merged

    # both authority links are present, the props survive the merge
    assert (
        collected,
        SKOS.exactMatch,
        DATACITE_DATE_TYPE_NAMESPACE["Collected"],
    ) in merged
    assert (collected, SKOS.exactMatch, URIRef(CCMM + "Collected")) in merged
    assert (collected, PROPS_NAMESPACE.datacite, Literal("Collected")) in merged

    # the id notation is not duplicated
    assert len(list(merged.objects(collected, SKOS.notation))) == 1


def test_date_types_merger_add_missing(monkeypatch):
    def make_source_with_extra() -> Graph:
        source = make_ccmm_source_graph()
        in_press = URIRef(CCMM + "InPress")
        source.add((URIRef(CCMM), SKOS.hasTopConcept, in_press))
        source.add((in_press, RDF.type, SKOS.Concept))
        source.add((in_press, SKOS.prefLabel, Literal("In Press", lang="en")))
        source.add((in_press, SKOS.prefLabel, Literal("V tisku", lang="cs")))
        return source

    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_source_with_extra())

    rdm = RDMDateTypesReader().read()
    ccmm = CCMMDateTypesReader(CCMM).read()

    # concepts without an RDM counterpart are skipped by default
    merged = DateTypesMerger(ccmm, rdm).merge()
    in_press = make_vocabulary_namespace("datetypes")["in-press"]
    assert (in_press, None, None) not in merged

    # ... and created complete with add_missing=True
    merged = DateTypesMerger(ccmm, rdm).merge(add_missing=True)
    assert (in_press, RDF.type, SKOS.Concept) in merged
    assert [str(n) for n in merged.objects(in_press, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "in-press"
    ]
    assert (in_press, SKOS.prefLabel, Literal("In Press", lang="en")) in merged
    assert (in_press, SKOS.prefLabel, Literal("V tisku", lang="cs")) in merged
    assert (in_press, SKOS.exactMatch, URIRef(CCMM + "InPress")) in merged

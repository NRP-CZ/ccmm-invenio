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
    DATACITE_DESCRIPTION_TYPE_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    CCMMDescriptionTypesReader,
    DescriptionTypesMerger,
    RDMDescriptionTypesReader,
)
from ccmm_invenio.fixtures.compiler.readers.skosmos import SkosmosReader

CCMM = "https://vocabs.ccmm.cz/registry/codelist/DescriptionType/"


def test_load_description_types():
    reader = RDMDescriptionTypesReader("uri:does_not_matter")
    description_types = reader.read()

    assert isinstance(description_types, Graph)

    vocab = make_vocabulary_namespace("descriptiontypes")

    # the well-known series-information type, carrying its DataCite
    # descriptionType
    series_information = vocab["series-information"]
    assert (series_information, RDF.type, SKOS.Concept) in description_types
    assert (series_information, SKOS.inScheme, URIRef(vocab)) in description_types
    assert [
        str(n)
        for n in description_types.objects(series_information, SKOS.notation)
        if n.datatype == NOTATION_ID_DATATYPE
    ] == ["series-information"]
    assert (series_information, SKOS.prefLabel, Literal("Series information", lang="en")) in description_types
    assert (series_information, SKOS.prefLabel, Literal("Informace o sérii", lang="cs")) in description_types

    assert (
        series_information,
        PROPS_NAMESPACE.datacite,
        Literal("SeriesInformation"),
    ) in description_types

    # the concept is matched to the DataCite descriptionType it maps to
    assert (
        series_information,
        SKOS.exactMatch,
        DATACITE_DESCRIPTION_TYPE_NAMESPACE["SeriesInformation"],
    ) in description_types
    assert (
        vocab["technical-info"],
        SKOS.exactMatch,
        DATACITE_DESCRIPTION_TYPE_NAMESPACE["TechnicalInfo"],
    ) in description_types

    # the vocabulary is flat: every entry is a top concept
    concepts = set(description_types.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(description_types.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(description_types.triples((None, SKOS.broader, None)))
    assert len(concepts) == 6

    # the prop is declared in the graph itself
    assert (PROPS_NAMESPACE.datacite, RDF.type, RDF.Property) in description_types
    assert (PROPS_NAMESPACE.datacite, RDFS.comment, None) in description_types


def make_ccmm_source_graph():
    """Return a mocked CCMM DescriptionType codelist with four description types."""
    source = Graph()
    source.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in (
        ("Abstract", "Abstract", "Abstrakt"),
        ("Methods", "Methods", "Metodologie"),
        ("SeriesInformation", "Series Information", "Informace o sérii"),
        ("TableOfContents", "Table Of Contents", "Obsah"),
        ("TechnicalInfo", "Technical Info", "Technická informace"),
        ("Other", "Other", "Jiný"),
    ):
        ccmm_uri = URIRef(CCMM + name)
        source.add((URIRef(CCMM), SKOS.hasTopConcept, ccmm_uri))
        source.add((ccmm_uri, RDF.type, SKOS.Concept))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(en, lang="en")))
        source.add((ccmm_uri, SKOS.prefLabel, Literal(cs, lang="cs")))
    return source


def test_ccmm_description_types(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    reader = CCMMDescriptionTypesReader(CCMM)
    graph = reader.read()

    vocab = make_vocabulary_namespace("descriptiontypes")

    # the CamelCase CCMM names become the kebab-case RDM ids
    series_information = vocab["series-information"]
    assert (series_information, RDF.type, SKOS.Concept) in graph
    assert (series_information, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(series_information, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "series-information"
    ]

    # linked to the CCMM authority, labels kept with their languages
    assert (series_information, SKOS.exactMatch, URIRef(CCMM + "SeriesInformation")) in graph
    assert (series_information, SKOS.prefLabel, Literal("Series Information", lang="en")) in graph
    assert (series_information, SKOS.prefLabel, Literal("Informace o sérii", lang="cs")) in graph

    # the other concepts round out the same six description types
    assert {str(c).rsplit("/", 1)[-1] for c in graph.subjects(RDF.type, SKOS.Concept)} == {
        "abstract",
        "methods",
        "series-information",
        "table-of-contents",
        "technical-info",
        "other",
    }


def test_description_types_merger(monkeypatch):
    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_ccmm_source_graph())

    rdm = RDMDescriptionTypesReader().read()
    ccmm = CCMMDescriptionTypesReader(CCMM).read()
    merged = DescriptionTypesMerger(ccmm, rdm).merge()

    vocab = make_vocabulary_namespace("descriptiontypes")
    methods = vocab["methods"]

    # the CCMM labels are single-valued per language - they replace the RDM
    # ones, so there is exactly one prefLabel per language
    assert (methods, SKOS.prefLabel, Literal("Methods", lang="en")) in merged
    assert (methods, SKOS.prefLabel, Literal("Metodologie", lang="cs")) in merged
    assert (methods, SKOS.prefLabel, Literal("Metody", lang="cs")) not in merged

    # the labels of unsupported languages are discarded when reading, so they
    # do not reach the merge at all
    assert (methods, SKOS.prefLabel, Literal("Methoden", lang="de")) not in merged

    # both authority links are present, the props survive the merge
    assert (
        methods,
        SKOS.exactMatch,
        DATACITE_DESCRIPTION_TYPE_NAMESPACE["Methods"],
    ) in merged
    assert (methods, SKOS.exactMatch, URIRef(CCMM + "Methods")) in merged
    assert (methods, PROPS_NAMESPACE.datacite, Literal("Methods")) in merged

    # the id notation is not duplicated
    assert len(list(merged.objects(methods, SKOS.notation))) == 1


def test_description_types_merger_add_missing(monkeypatch):
    def make_source_with_extra() -> Graph:
        source = make_ccmm_source_graph()
        provenance = URIRef(CCMM + "Provenance")
        source.add((URIRef(CCMM), SKOS.hasTopConcept, provenance))
        source.add((provenance, RDF.type, SKOS.Concept))
        source.add((provenance, SKOS.prefLabel, Literal("Provenance", lang="en")))
        source.add((provenance, SKOS.prefLabel, Literal("Provenience", lang="cs")))
        return source

    monkeypatch.setattr(SkosmosReader, "fetch_source", lambda _self: make_source_with_extra())

    rdm = RDMDescriptionTypesReader().read()
    ccmm = CCMMDescriptionTypesReader(CCMM).read()

    # concepts without an RDM counterpart are skipped by default
    merged = DescriptionTypesMerger(ccmm, rdm).merge()
    provenance = make_vocabulary_namespace("descriptiontypes")["provenance"]
    assert (provenance, None, None) not in merged

    # ... and created complete with add_missing=True
    merged = DescriptionTypesMerger(ccmm, rdm).merge(add_missing=True)
    assert (provenance, RDF.type, SKOS.Concept) in merged
    assert [str(n) for n in merged.objects(provenance, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "provenance"
    ]
    assert (provenance, SKOS.prefLabel, Literal("Provenance", lang="en")) in merged
    assert (provenance, SKOS.prefLabel, Literal("Provenience", lang="cs")) in merged
    assert (provenance, SKOS.exactMatch, URIRef(CCMM + "Provenance")) in merged

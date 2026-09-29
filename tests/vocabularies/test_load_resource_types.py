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
    DATACITE_RESOURCE_TYPE_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    COARResourceTypesReader,
    RDMResourceTypesReader,
    ResourceTypesMerger,
    SSSOMMappingsReader,
)
from ccmm_invenio.fixtures.compiler.readers.resource_types import COAR_RESOURCE_TYPE_EXPIRES


def test_load_resource_types():
    reader = RDMResourceTypesReader("uri:does_not_matter")
    resource_types = reader.read()

    assert isinstance(resource_types, Graph)

    vocab = make_vocabulary_namespace("resourcetypes")

    # the well-known publication-book subtype, mapped to DataCite Book
    book = vocab["publication-book"]
    assert (book, RDF.type, SKOS.Concept) in resource_types
    assert (book, SKOS.inScheme, URIRef(vocab)) in resource_types
    assert [str(n) for n in resource_types.objects(book, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "publication-book"
    ]
    assert (book, SKOS.prefLabel, Literal("Book", lang="en")) in resource_types
    assert (book, SKOS.prefLabel, Literal("Kniha", lang="cs")) in resource_types

    # the fixture props, as PROPS_NAMESPACE predicates
    assert (book, PROPS_NAMESPACE.datacite_general, Literal("Book")) in resource_types
    assert (book, PROPS_NAMESPACE.csl, Literal("book")) in resource_types
    assert (book, PROPS_NAMESPACE.openaire_resourceType, Literal("0002")) in resource_types
    assert (book, PROPS_NAMESPACE["schema.org"], Literal("https://schema.org/Book")) in resource_types
    # type and subtype are kept among the props
    assert (book, PROPS_NAMESPACE["type"], Literal("publication")) in resource_types
    assert (book, PROPS_NAMESPACE["subtype"], Literal("publication-book")) in resource_types
    # empty values are skipped, so there is no datacite_type prop
    assert (book, PROPS_NAMESPACE.datacite_type, None) not in resource_types

    assert (book, TAGS_URI, Literal("depositable")) in resource_types

    # the concept is matched to the DataCite resourceTypeGeneral it maps to
    assert (
        book,
        SKOS.broadMatch,
        DATACITE_RESOURCE_TYPE_NAMESPACE["Book"],
    ) in resource_types
    # ... and to the broader schema.org class it maps to
    assert (
        book,
        SKOS.broadMatch,
        URIRef("https://schema.org/Book"),
    ) in resource_types

    # subtypes hang below their parent via broader/narrower ...
    publication = vocab["publication"]
    assert (book, SKOS.broader, publication) in resource_types
    assert (publication, SKOS.narrower, book) in resource_types

    # ... and the parents are the top concepts
    assert (publication, SKOS.topConceptOf, URIRef(vocab)) in resource_types
    assert (URIRef(vocab), SKOS.hasTopConcept, publication) in resource_types
    assert (publication, SKOS.prefLabel, Literal("Publication", lang="en")) in resource_types

    # the props are declared in the graph itself
    for prop in (PROPS_NAMESPACE.csl, PROPS_NAMESPACE["schema.org"]):
        assert (prop, RDF.type, RDF.Property) in resource_types
        assert (prop, RDFS.comment, None) in resource_types


COAR = "http://purl.org/coar/resource_type/"


def make_coar_source_graph():
    """Return a mocked COAR resource types vocabulary.

    A fragment of the real one (version 3.2): the book (c_2f33) and the
    research article (c_2df8fbb1) with their hierarchy links, the text
    (c_18cf) on the top, the design patent (C53B-JCY5) with an uppercase
    code and the cartoon (GSZA-Y7V7) hanging below the deprecated blog post
    (c_2659) - which COAR marks as expired.
    """
    source = Graph()
    scheme = URIRef(COAR + "scheme")
    source.add((scheme, RDF.type, SKOS.ConceptScheme))

    def concept(code, labels=(), broader=(), narrower=(), expires=None) -> URIRef:
        uri = URIRef(COAR + code)
        source.add((uri, RDF.type, SKOS.Concept))
        source.add((uri, SKOS.inScheme, scheme))
        for lang, label in labels:
            source.add((uri, SKOS.prefLabel, Literal(label, lang=lang)))
        for parent in broader:
            source.add((uri, SKOS.broader, URIRef(COAR + parent)))
        for child in narrower:
            source.add((uri, SKOS.narrower, URIRef(COAR + child)))
        if expires is not None:
            source.add((uri, COAR_RESOURCE_TYPE_EXPIRES, Literal(expires)))
        return uri

    # the book, matched to the RDM publication-book by the mapping set
    book = concept(
        "c_2f33",
        labels={("en", "book"), ("cs", "kniha"), ("ja", "本")},
        broader={"c_18cf"},
    )
    source.add((book, SKOS.definition, Literal("A non-serial publication complete in one volume.", lang="en")))
    source.add((book, SKOS.exactMatch, URIRef("http://purl.org/eprint/type/Book")))
    source.add((book, SKOS.relatedMatch, URIRef("https://schema.org/Book")))

    # the text, a top concept the RDM vocabulary does not cover
    concept("c_18cf", labels={("en", "text"), ("cs", "text")}, narrower={"c_2f33"})

    # the article and the patent, matched to the RDM article and patent types
    concept("c_6501", labels={("en", "article")})
    concept("c_15cd", labels={("en", "patent")})

    # the research article, below the article concept of the RDM vocabulary
    concept("c_2df8fbb1", labels={("en", "research article"), ("cs", "vědecký článek")}, broader={"c_6501"})

    # the design patent, below the patent type of the RDM vocabulary
    concept("C53B-JCY5", labels={("en", "design patent"), ("cs", "průmyslový vzor")}, broader={"c_15cd"})

    # the cartoon, below the deprecated blog post - its parent is not read
    concept("GSZA-Y7V7", labels={("en", "cartoon")}, broader={"c_2659"})

    # the deprecated blog post, expired and skipped by the reader
    concept("c_2659", labels={("en", "blog post")}, expires="2021-03-12")
    return source


def read_coar_resource_types(monkeypatch):
    """Return the mocked COAR resource types, read into the NMA namespace."""
    monkeypatch.setattr(COARResourceTypesReader, "fetch_source", lambda _self: make_coar_source_graph())
    return COARResourceTypesReader().read()


def test_coar_resource_types_reader(monkeypatch):
    resource_types = read_coar_resource_types(monkeypatch)

    vocab = make_vocabulary_namespace("resourcetypes")

    # the concepts are re-homed under their lowercased COAR codes ...
    patent = vocab["c53b-jcy5"]
    assert (patent, RDF.type, SKOS.Concept) in resource_types
    assert [str(n) for n in resource_types.objects(patent, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "c53b-jcy5"
    ]

    # ... linked back to the COAR authority ...
    assert (patent, SKOS.exactMatch, URIRef(COAR + "C53B-JCY5")) in resource_types

    # ... keeping their labels in the supported languages only
    assert (patent, SKOS.prefLabel, Literal("design patent", lang="en")) in resource_types
    assert (patent, SKOS.prefLabel, Literal("průmyslový vzor", lang="cs")) in resource_types

    # the expired concept is not read at all
    assert (vocab["c_2659"], RDF.type, SKOS.Concept) not in resource_types

    book = vocab["c_2f33"]
    assert (book, RDF.type, SKOS.Concept) in resource_types
    assert (book, SKOS.prefLabel, Literal("book", lang="en")) in resource_types
    assert (book, SKOS.prefLabel, Literal("kniha", lang="cs")) in resource_types
    assert (book, SKOS.prefLabel, Literal("本", lang="ja")) not in resource_types
    assert (book, SKOS.definition, None) in resource_types

    # the foreign mapping links of the COAR concepts are kept ...
    assert (book, SKOS.exactMatch, URIRef("http://purl.org/eprint/type/Book")) in resource_types
    assert (book, SKOS.relatedMatch, URIRef("https://schema.org/Book")) in resource_types

    # ... but the hierarchy still points at the COAR concepts - it is the
    # merger that re-targets it to the vocabulary concepts - and is carried
    # by the broader links only, the narrower ones are dropped
    assert (book, SKOS.broader, URIRef(COAR + "c_18cf")) in resource_types
    assert not list(resource_types.triples((None, SKOS.narrower, None)))

    # the scheme placement is the business of the merger as well: the reader
    # cannot know which concepts the target vocabulary covers
    assert not list(resource_types.triples((None, SKOS.topConceptOf, None)))
    assert not list(resource_types.triples((None, SKOS.hasTopConcept, None)))


def test_resource_types_merger(monkeypatch):
    coar = read_coar_resource_types(monkeypatch)

    # the RDM vocabulary with the mapping set merged in, as the converter
    # builds it - the mapping set links the RDM types to the COAR concepts
    from ccmm_invenio.fixtures.compiler.converter import DATA_DIR, overlay

    rdm = overlay(
        RDMResourceTypesReader().read(),
        SSSOMMappingsReader(DATA_DIR / "resource_types.yaml"),
    )
    resource_types = ResourceTypesMerger(coar, rdm).merge(add_missing=True)

    vocab = make_vocabulary_namespace("resourcetypes")

    # the book has its RDM counterpart (publication-book, linked by the
    # mapping set): it is not added and the curated RDM data stays
    assert (vocab["c_2f33"], RDF.type, SKOS.Concept) not in resource_types
    book = vocab["publication-book"]
    assert (book, SKOS.prefLabel, Literal("Book", lang="en")) in resource_types
    assert (book, SKOS.prefLabel, Literal("book", lang="en")) not in resource_types

    # the text the RDM vocabulary does not cover is added as a top concept,
    # linked to the scheme in both directions
    text = vocab["c_18cf"]
    assert (text, RDF.type, SKOS.Concept) in resource_types
    assert [str(n) for n in resource_types.objects(text, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "c_18cf"
    ]
    assert (text, SKOS.prefLabel, Literal("text", lang="en")) in resource_types
    assert (text, SKOS.exactMatch, URIRef(COAR + "c_18cf")) in resource_types
    assert (text, SKOS.topConceptOf, URIRef(vocab)) in resource_types
    assert (URIRef(vocab), SKOS.hasTopConcept, text) in resource_types

    # the research article is added below the article type of the RDM
    # vocabulary - its broader link re-targeted to the counterpart
    article = vocab["c_2df8fbb1"]
    assert (article, RDF.type, SKOS.Concept) in resource_types
    assert (article, SKOS.broader, vocab["publication-article"]) in resource_types
    assert (article, SKOS.topConceptOf, URIRef(vocab)) not in resource_types

    # the design patent the same, below the patent type
    patent = vocab["c53b-jcy5"]
    assert (patent, RDF.type, SKOS.Concept) in resource_types
    assert (patent, SKOS.broader, vocab["publication-patent"]) in resource_types

    # the hierarchy is carried by the broader links only: the merge adds no
    # narrower link, not even from the counterparts the children hang below
    assert (vocab["publication-article"], SKOS.narrower, article) not in resource_types
    assert (vocab["publication-patent"], SKOS.narrower, patent) not in resource_types
    assert (text, SKOS.narrower, book) not in resource_types

    # the cartoon is added without its parent - the deprecated blog post was
    # not read, so the link to it is dropped and it stays a top concept
    cartoon = vocab["gsza-y7v7"]
    assert (cartoon, RDF.type, SKOS.Concept) in resource_types
    assert (cartoon, SKOS.broader, None) not in resource_types
    assert (cartoon, SKOS.topConceptOf, URIRef(vocab)) in resource_types

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
    EUROPA_LANGUAGE_NAMESPACE,
    EUVOC_NAMESPACE,
    MISSING_EUROPA_LANGUAGE_CODES,
    NMA_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.declarations import semantic_declarations
from ccmm_invenio.fixtures.compiler.readers import (
    LanguageReader,
    PrimaryLanguagesReader,
)
from ccmm_invenio.fixtures.compiler.readers.base import keep_value


def test_semantic_declarations_merge():
    """The declarations graph can be built standalone and merged into any graph."""
    declarations = semantic_declarations()

    assert isinstance(declarations, Graph)
    assert (NOTATION_ID_DATATYPE, RDF.type, RDFS.Datatype) in declarations

    # every namespace/uri constant is described
    described = [
        URIRef(NMA_NAMESPACE),
        URIRef(PROPS_NAMESPACE),
        TAGS_URI,
        URIRef(EUROPA_LANGUAGE_NAMESPACE),
        NOTATION_ID_DATATYPE,
    ]
    for uri in described:
        assert (uri, RDFS.label, None) in declarations, uri
        assert (uri, RDFS.comment, None) in declarations, uri

    graph = Graph()
    graph += declarations
    assert (NOTATION_ID_DATATYPE, RDF.type, RDFS.Datatype) in graph
    # merging does not consume the declarations graph
    assert len(declarations) > 0


def test_load_languages():
    reader = LanguageReader("uri:does_not_matter")
    languages = reader.read()

    assert isinstance(languages, Graph)

    # the id-notation datatype is declared and documented in the graph itself
    assert (NOTATION_ID_DATATYPE, RDF.type, RDFS.Datatype) in languages
    assert (NOTATION_ID_DATATYPE, RDFS.label, Literal("NMA internal vocabulary id", lang="en")) in languages

    ces = make_vocabulary_namespace("languages")["CES"]
    assert (ces, SKOS.notation, Literal("ces", datatype=NOTATION_ID_DATATYPE)) in languages
    # our notations are identifiable by their datatype among any foreign ones
    assert [str(n) for n in languages.objects(ces, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["ces"]
    assert (ces, RDF.type, SKOS.Concept) in languages
    assert (ces, SKOS.inScheme, URIRef(make_vocabulary_namespace("languages"))) in languages
    assert (ces, SKOS.prefLabel, Literal("Czech", lang="en")) in languages
    assert (ces, SKOS.prefLabel, Literal("čeština", lang="cs")) in languages
    assert (
        ces,
        SKOS.exactMatch,
        EUROPA_LANGUAGE_NAMESPACE["CES"],
    ) in languages
    assert (ces, PROPS_NAMESPACE.alpha_2, Literal("cs")) in languages
    assert (ces, PROPS_NAMESPACE.xml_lang, Literal("cs")) in languages

    # euvoc-typed notations, mirroring the europa language authority
    assert (ces, SKOS.notation, Literal("cs", datatype=EUVOC_NAMESPACE.XML_LNG)) in languages
    assert (ces, SKOS.notation, Literal("cs", datatype=EUVOC_NAMESPACE.ISO_639_1)) in languages
    assert (ces, SKOS.notation, Literal("ces", datatype=EUVOC_NAMESPACE.ISO_639_3)) in languages

    # Alumu-Tesu has no ISO 639-1 code, so xml_lang falls back to the 639-3 code
    aab = make_vocabulary_namespace("languages")["AAB"]
    assert (aab, PROPS_NAMESPACE.alpha_2, None) not in languages
    assert (aab, PROPS_NAMESPACE.xml_lang, Literal("aab")) in languages
    assert (aab, SKOS.notation, Literal("aab", datatype=EUVOC_NAMESPACE.XML_LNG)) in languages
    assert (aab, SKOS.notation, Literal("aab", datatype=EUVOC_NAMESPACE.ISO_639_3)) in languages
    assert not [n for n in languages.objects(aab, SKOS.notation) if n.datatype == EUVOC_NAMESPACE.ISO_639_1]

    # Interslavic (isv) has no counterpart in the EU language authority
    isv = make_vocabulary_namespace("languages")["ISV"]
    assert (isv, SKOS.exactMatch, None) not in languages

    # every language except the missing ones must link to its europa counterpart
    for concept_uri in languages.subjects(RDF.type, SKOS.Concept):
        code = str(concept_uri).rsplit("/", 1)[1].lower()
        if code in MISSING_EUROPA_LANGUAGE_CODES:
            assert not list(languages.objects(concept_uri, SKOS.exactMatch))
        else:
            assert EUROPA_LANGUAGE_NAMESPACE[code.upper()] in languages.objects(concept_uri, SKOS.exactMatch)


def test_load_primary_languages():
    languages = LanguageReader("uri:does_not_matter").read()
    primary = PrimaryLanguagesReader(lambda: languages).read()

    # only the languages with an ISO 639-1 code survive the filter - and und (Undetermined),
    # the language of the texts without one
    primary_concepts = set(primary.subjects(RDF.type, SKOS.Concept))
    assert primary_concepts == {
        concept
        for concept in languages.subjects(RDF.type, SKOS.Concept)
        if any(notation.datatype == EUVOC_NAMESPACE.ISO_639_1 for notation in languages.objects(concept, SKOS.notation))
    } | {make_vocabulary_namespace("languages")["UND"]}

    # Czech carries its ISO 639-1 code, Alumu-Tesu does not
    ces = make_vocabulary_namespace("languages")["CES"]
    aab = make_vocabulary_namespace("languages")["AAB"]
    assert (ces, RDF.type, SKOS.Concept) in primary
    assert (aab, RDF.type, SKOS.Concept) not in primary
    assert not list(primary.predicate_objects(aab))

    # the semantic declarations stay, the full vocabulary is not consumed
    assert (NOTATION_ID_DATATYPE, RDF.type, RDFS.Datatype) in primary
    assert (ces, RDF.type, SKOS.Concept) in languages
    assert (aab, RDF.type, SKOS.Concept) in languages


def test_labels_in_supported_languages_only():
    """The labels and descriptions of the languages are read in cs/en only."""
    languages = LanguageReader("uri:does_not_matter").read()
    for predicate in (SKOS.prefLabel, SKOS.definition):
        for label in languages.objects(None, predicate):
            assert label.language in (None, "cs", "en"), label

    ces = make_vocabulary_namespace("languages")["CES"]
    assert sorted(str(label) for label in languages.objects(ces, SKOS.prefLabel)) == [
        "Czech",
        "čeština",
    ]


def test_keep_value():
    """Only language-tagged labels and definitions are filtered by language."""
    assert keep_value(SKOS.prefLabel, Literal("Uveďte původ", lang="cs"))
    assert keep_value(SKOS.prefLabel, Literal("Attribution", lang="en"))
    assert keep_value(SKOS.definition, Literal("Attribution", lang="en"))
    # plain literals pass (they map to English on the export)
    assert keep_value(SKOS.prefLabel, Literal("plain"))
    # other languages are dropped from labels and descriptions
    assert not keep_value(SKOS.prefLabel, Literal("Namensnennung", lang="de"))
    assert not keep_value(SKOS.definition, Literal("Namensnennung", lang="de"))
    # altLabels are labels as well; other predicates are not filtered
    assert not keep_value(SKOS.altLabel, Literal("CC BY", lang="fr"))
    assert keep_value(SKOS.exactMatch, URIRef("https://example.org/by"))
    assert keep_value(SKOS.notation, Literal("by", datatype=EUVOC_NAMESPACE.ISO_639_1))

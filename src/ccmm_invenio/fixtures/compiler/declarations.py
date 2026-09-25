#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Graph of semantic declarations (datatypes, namespaces, ...) shared by vocabularies.

Merge it into a vocabulary graph with ``graph += semantic_declarations()``.
"""

from __future__ import annotations

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Literal, URIRef

from .constants import (
    EUROPA_LANGUAGE_NAMESPACE,
    EUVOC_NAMESPACE,
    NMA_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    TAGS_URI,
)

RESOURCE_TYPE_PROPS = {
    "csl": "Citation Style Language (CSL) type of a resource type.",
    "datacite_general": "DataCite resourceTypeGeneral of a resource type.",
    "datacite_type": "DataCite resource type name, when the general one is further specified.",
    "openaire_resourceType": "OpenAIRE resource type code of a resource type.",
    "openaire_type": "OpenAIRE type name of a resource type.",
    "eurepo": "eu-repo semantics identifier of a resource type.",
    "schema.org": "schema.org type a resource type maps to.",
    "marc21_type": "MARC 21 type of record of a resource type.",
    "marc21_subtype": "MARC 21 bibliographic level of a resource type.",
    "type": "InvenioRDM resource type id a resource type belongs to.",
    "subtype": "InvenioRDM resource subtype id; empty for top-level types.",
}


def declare(graph: Graph, term: URIRef, term_type: URIRef, label: str, comment: str) -> None:
    """Add the type, label and comment triples describing a term."""
    graph.add((term, RDF.type, term_type))
    graph.add((term, RDFS.label, Literal(label, lang="en")))
    graph.add((term, RDFS.comment, Literal(comment, lang="en")))


def semantic_declarations() -> Graph:
    """Build a graph of declarations describing our semantic constructs."""
    graph = Graph()

    # our own namespaces
    declare(
        graph,
        URIRef(NMA_NAMESPACE),
        OWL.Ontology,
        "NMA vocabularies",
        "Namespace of the NMA vocabularies; each sub-path is one vocabulary (e.g. languages).",
    )
    declare(
        graph,
        URIRef(PROPS_NAMESPACE),
        OWL.Ontology,
        "NMA vocabulary properties",
        "Namespace of internal vocabulary properties and datatypes "
        "used for round-tripping vocabulary data; not intended for "
        "external compatibility.",
    )

    # TAGS_URI is used as a predicate linking concepts to their tag values
    declare(
        graph,
        TAGS_URI,
        RDF.Property,
        "vocabulary tags",
        "Links a vocabulary concept to its tag values (e.g. the scope and type of a language); internal use.",
    )

    # the vocabulary properties themselves
    declare(
        graph,
        PROPS_NAMESPACE.alpha_2,
        RDF.Property,
        "ISO 639-1 code",
        "Two-letter ISO 639-1 code of a language, when it has one.",
    )
    declare(
        graph,
        PROPS_NAMESPACE.xml_lang,
        RDF.Property,
        "xml:lang code",
        "Language tag suitable for an xml:lang attribute: the ISO 639-1 "
        "code when available, the ISO 639-3 code otherwise.",
    )
    declare(
        graph,
        PROPS_NAMESPACE.datacite,
        RDF.Property,
        "DataCite relationType name",
        "Name of the DataCite relationType (e.g. IsCitedBy) a relation type concept stands for.",
    )
    declare(
        graph,
        PROPS_NAMESPACE.classification_code,
        RDF.Property,
        "classification code",
        "Code of a subject in its classification scheme (e.g. the FORD code 10101 or the INSPIRE theme code EF).",
    )
    declare(
        graph,
        PROPS_NAMESPACE.marc,
        RDF.Property,
        "MARC 21 relator code",
        "Three-letter MARC 21 relator code (e.g. prc) of a role concept.",
    )

    for prop_name, comment in RESOURCE_TYPE_PROPS.items():
        declare(graph, PROPS_NAMESPACE[prop_name], RDF.Property, prop_name, comment)

    # the EU Publications Office language authority our languages link to
    europa = URIRef(EUROPA_LANGUAGE_NAMESPACE)
    declare(
        graph,
        europa,
        SKOS.ConceptScheme,
        "EU Publications Office language authority",
        "EU Publications Office language authority table; identifiers are ISO 639-3 codes.",
    )
    graph.add((europa, RDFS.seeAlso, URIRef("https://op.europa.eu/en/web/eu-vocabularies")))

    # the EU Vocabularies ontology providing the notation datatypes
    # (the ontology IRI is the namespace without the '#' separator)
    euvoc = URIRef(str(EUVOC_NAMESPACE).rstrip("#"))
    declare(
        graph,
        euvoc,
        OWL.Ontology,
        "EU Vocabularies ontology (euvoc)",
        "Ontology of the EU Publications Office; its terms are used as "
        "skos:notation datatypes to distinguish language code schemes "
        "(e.g. ISO_639_1, ISO_639_3, XML_LNG).",
    )
    graph.add((euvoc, RDFS.seeAlso, URIRef("https://op.europa.eu/en/web/eu-vocabularies")))

    # the id-notation datatype
    declare(
        graph,
        NOTATION_ID_DATATYPE,
        RDFS.Datatype,
        "NMA internal vocabulary id",
        "Marks skos:notation literals carrying the internal NMA "
        "vocabulary id, used for round-tripping vocabulary data; "
        "not intended for external compatibility.",
    )

    return graph

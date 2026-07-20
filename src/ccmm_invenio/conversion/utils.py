#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Utility functions and SPARQL query templates for vocabulary conversion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ccmm_invenio.conversion.rdf_store import RDFTripleStore


# SPARQL query templates
QUERIES = {
    "list_concepts": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>

        SELECT ?concept ?id ?labelEn ?labelCs
        WHERE {
            ?concept a skos:Concept .
            OPTIONAL { ?concept dc:identifier ?id }
            OPTIONAL { ?concept skos:prefLabel ?labelEn FILTER(lang(?labelEn) = "en") }
            OPTIONAL { ?concept skos:prefLabel ?labelCs FILTER(lang(?labelCs) = "cs") }
        }
        ORDER BY ?id
    """,
    "concept_details": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>

        SELECT ?property ?value
        WHERE {
            ?concept a skos:Concept .
            FILTER(?concept = <{concept_uri}>)
            ?concept ?property ?value .
        }
    """,
    "concept_hierarchy": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>

        SELECT ?concept ?id ?parent ?parentId ?label
        WHERE {
            ?concept a skos:Concept .
            ?concept dc:identifier ?id .
            OPTIONAL {
                # Try skos:broader first (for internal hierarchy)
                { ?concept skos:broader ?parent . }
                UNION
                # Then try skos:broadMatch (for cross-scheme mappings)
                { ?concept skos:broadMatch ?parent . }
                ?parent dc:identifier ?parentId .
            }
            OPTIONAL { ?concept skos:prefLabel ?label FILTER(lang(?label) = "en") }
        }
        ORDER BY ?parentId ?id
    """,
    "concept_schemes": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT DISTINCT ?scheme (COUNT(?concept) as ?conceptCount)
        WHERE {
            ?concept a skos:Concept .
            ?concept skos:inScheme ?scheme .
        }
        GROUP BY ?scheme
        ORDER BY ?scheme
    """,
    "mappings": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?source ?target ?predicate
        WHERE {
            ?source ?predicate ?target .
            FILTER(?predicate IN (
                skos:exactMatch,
                skos:closeMatch,
                skos:broadMatch,
                skos:narrowMatch,
                skos:relatedMatch,
                owl:sameAs
            ))
        }
        ORDER BY ?source ?predicate
    """,
    "statistics": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT
            (COUNT(DISTINCT ?concept) as ?concepts)
            (COUNT(DISTINCT ?scheme) as ?schemes)
            (COUNT(DISTINCT ?match) as ?mappings)
        WHERE {
            {
                ?concept a skos:Concept .
                OPTIONAL { ?concept skos:inScheme ?scheme }
            }
            UNION
            {
                ?source ?matchPred ?match .
                FILTER(?matchPred IN (
                    skos:exactMatch, skos:closeMatch,
                    skos:broadMatch, skos:narrowMatch,
                    skos:relatedMatch, owl:sameAs
                ))
            }
        }
    """,
}


def query_concepts(store: RDFTripleStore) -> list[dict[str, Any]]:
    """Query all concepts from the triplestore.

    Args:
        store: The RDF triplestore

    Returns:
        List of concept dictionaries

    """
    results = store.query(QUERIES["list_concepts"])
    concepts = []

    for row in results:
        concepts.append(
            {
                "uri": str(row.concept),
                "id": str(row.id) if row.id else None,
                "label_en": str(row.labelEn) if row.labelEn else None,
                "label_cs": str(row.labelCs) if row.labelCs else None,
            }
        )

    return concepts


def query_concept_schemes(store: RDFTripleStore) -> list[dict[str, Any]]:
    """Query all concept schemes and their sizes.

    Args:
        store: The RDF triplestore

    Returns:
        List of scheme dictionaries

    """
    results = store.query(QUERIES["concept_schemes"])
    schemes = []

    for row in results:
        schemes.append(
            {
                "uri": str(row.scheme),
                "count": int(row.conceptCount),
            }
        )

    return schemes


def query_hierarchy(store: RDFTripleStore) -> list[dict[str, Any]]:
    """Query the concept hierarchy.

    Args:
        store: The RDF triplestore

    Returns:
        List of concepts with parent relationships

    """
    results = store.query(QUERIES["concept_hierarchy"])
    hierarchy = []

    for row in results:
        hierarchy.append(
            {
                "uri": str(row.concept),
                "id": str(row.id) if row.id else None,
                "parent_uri": str(row.parent) if row.parent else None,
                "parent_id": str(row.parentId) if row.parentId else None,
                "label": str(row.label) if row.label else None,
            }
        )

    return hierarchy


def query_mappings(store: RDFTripleStore) -> list[dict[str, Any]]:
    """Query all mappings between concepts.

    Args:
        store: The RDF triplestore

    Returns:
        List of mapping dictionaries

    """
    results = store.query(QUERIES["mappings"])
    mappings = []

    for row in results:
        mappings.append(
            {
                "source": str(row.source),
                "target": str(row.target),
                "predicate": str(row.predicate),
            }
        )

    return mappings


def query_statistics(store: RDFTripleStore) -> dict[str, int]:
    """Query triplestore statistics.

    Args:
        store: The RDF triplestore

    Returns:
        Dictionary with statistics

    """
    results = store.query(QUERIES["statistics"])

    for row in results:
        return {
            "concepts": int(row.concepts) if row.concepts else 0,
            "schemes": int(row.schemes) if row.schemes else 0,
            "mappings": int(row.mappings) if row.mappings else 0,
            "triples": store.size(),
        }

    return {"concepts": 0, "schemes": 0, "mappings": 0, "triples": store.size()}


def print_statistics(store: RDFTripleStore) -> None:
    """Print triplestore statistics to console.

    Args:
        store: The RDF triplestore

    """
    stats = query_statistics(store)

    print("\n=== Triplestore Statistics ===")
    print(f"Total triples:   {stats['triples']:,}")
    print(f"Concepts:        {stats['concepts']:,}")
    print(f"Concept schemes: {stats['schemes']:,}")
    print(f"Mappings:        {stats['mappings']:,}")
    print("==============================\n")


def print_concept_schemes(store: RDFTripleStore) -> None:
    """Print all concept schemes to console.

    Args:
        store: The RDF triplestore

    """
    schemes = query_concept_schemes(store)

    print("\n=== Concept Schemes ===")
    for scheme in schemes:
        print(f"{scheme['uri']}")
        print(f"  Concepts: {scheme['count']}")
    print("=======================\n")

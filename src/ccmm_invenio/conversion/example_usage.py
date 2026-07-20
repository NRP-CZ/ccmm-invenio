#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Example script demonstrating the RDF vocabulary conversion system."""

from pathlib import Path

from ccmm_invenio.conversion.csv_loader import CSVToRDFLoader
from ccmm_invenio.conversion.rdf_store import RDFTripleStore
from ccmm_invenio.conversion.utils import (
    print_concept_schemes,
    print_statistics,
    query_concepts,
    query_hierarchy,
)


def main() -> None:
    """Run example demonstrating the vocabulary conversion workflow.

    Note: This is an example script that intentionally uses print statements
    for demonstration purposes.
    """
    print("=" * 60)
    print("CCMM Vocabulary Conversion - Example Usage")
    print("=" * 60)

    # Step 1: Initialize triplestore
    print("\n1. Initializing RDF triplestore...")
    store = RDFTripleStore()
    print(f"   Created empty triplestore with {store.size()} triples")

    # Step 2: Load CSV data
    print("\n2. Loading CSV vocabulary data...")
    csv_loader = CSVToRDFLoader(store)

    # Get the input directory
    input_dir = Path(__file__).parent.parent / "input"

    # Load a single file as an example
    agent_roles_csv = input_dir / "CCMM_slovniky(AgentRole).csv"
    if agent_roles_csv.exists():
        count = csv_loader.load_csv_file(agent_roles_csv)
        print(f"   Loaded {count} agent role concepts")
    else:
        print(f"   Warning: {agent_roles_csv} not found")

    # Step 3: Demonstrate querying
    print("\n3. Querying the triplestore...")

    # Get statistics
    print_statistics(store)

    # List concept schemes
    print_concept_schemes(store)

    # Show first few concepts
    concepts = query_concepts(store)
    print("   First 5 concepts:")
    for concept in concepts[:5]:
        print(f"   - {concept['id']}: {concept['label_en'] or concept['label_cs']}")

    # Show hierarchy
    print("\n4. Concept hierarchy:")
    hierarchy = query_hierarchy(store)

    # Group by parent
    by_parent = {}
    for item in hierarchy:
        parent = item["parent_id"] or "(root)"
        if parent not in by_parent:
            by_parent[parent] = []
        by_parent[parent].append(item)

    # Show root concepts and their children
    if "(root)" in by_parent:
        print("   Root concepts:")
        for item in by_parent["(root)"][:5]:  # Show first 5
            print(f"   - {item['id']}: {item['label']}")
            if item["id"] in by_parent:
                for child in by_parent[item["id"]][:3]:  # Show first 3 children
                    print(f"     └─ {child['id']}: {child['label']}")

    # Step 5: Export to different RDF formats
    print("\n5. Exporting to different formats...")

    # Export as Turtle
    turtle = store.serialize(format="turtle")
    print(f"   Turtle format: {len(turtle)} characters")
    print("   First 500 characters:")
    print("   " + "\n   ".join(turtle[:500].split("\n")))

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)

    # Optional: Show how to add custom namespaces
    print("\n6. Adding custom namespaces (example):")
    store.bind_namespace("ex", "http://example.org/")
    print("   Added 'ex' namespace")

    # Optional: Show a custom SPARQL query
    print("\n7. Custom SPARQL query example:")
    query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?concept (COUNT(?narrower) as ?childCount)
        WHERE {
            ?concept a skos:Concept .
            OPTIONAL {
                # Check for narrower concepts using skos:broader (internal hierarchy)
                { ?narrower skos:broader ?concept . }
                UNION
                # Also check using skos:broadMatch (cross-scheme mappings)
                { ?narrower skos:broadMatch ?concept . }
            }
        }
        GROUP BY ?concept
        HAVING (?childCount > 0)
        ORDER BY DESC(?childCount)
        LIMIT 5
    """

    results = store.query(query)
    print("   Concepts with most children:")
    for row in results:
        print(f"   - {row.concept}: {row.childCount} children")


if __name__ == "__main__":
    main()

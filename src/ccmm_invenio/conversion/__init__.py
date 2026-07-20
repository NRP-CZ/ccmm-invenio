#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""RDF-based vocabulary conversion system for CCMM Invenio.

This package provides a modular system for converting vocabularies from
various sources (CSV, SPARQL endpoints, SSSOM mappings) into a unified
RDF triplestore, which can then be queried and exported to Invenio fixtures.

Main components:
- RDFTripleStore: In-memory RDF graph with namespace management
- CSVToRDFLoader: Load CSV vocabulary files
- SPARQLLoader: Load vocabularies from RDF sources
- SSSOMLoader: Load SSSOM mapping files
- Utilities: Query helpers and statistics

Example usage:
    >>> from ccmm_invenio.conversion import (
    ...     RDFTripleStore,
    ...     CSVToRDFLoader,
    ... )
    >>> store = RDFTripleStore()
    >>> loader = CSVToRDFLoader(store)
    >>> loader.load_directory(Path("input"))

See README.md for detailed documentation.
"""

from ccmm_invenio.conversion.csv_loader import CSVToRDFLoader
from ccmm_invenio.conversion.rdf_store import RDFTripleStore
from ccmm_invenio.conversion.sparql_loader import SPARQLLoader
from ccmm_invenio.conversion.sssom_loader import SSSOMLoader
from ccmm_invenio.conversion.utils import (
    print_concept_schemes,
    print_statistics,
    query_concept_schemes,
    query_concepts,
    query_hierarchy,
    query_mappings,
    query_statistics,
)

__all__ = [
    # Core components
    "CSVToRDFLoader",
    "RDFTripleStore",
    "SPARQLLoader",
    "SSSOMLoader",
    # Display utilities
    "print_concept_schemes",
    "print_statistics",
    # Query utilities
    "query_concept_schemes",
    "query_concepts",
    "query_hierarchy",
    "query_mappings",
    "query_statistics",
]

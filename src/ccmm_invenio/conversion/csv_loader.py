#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Load CSV vocabulary data into RDF triplestore."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS

from .loader import VocabularyLoader

if TYPE_CHECKING:
    from ccmm_invenio.conversion.rdf_store import RDFTripleStore

log = logging.getLogger(__name__)

# CCMM namespace
CCMM = Namespace("https://vocabs.ccmm.cz/registry/codelist/")
CCMM_PROPS = Namespace("http://vocabs.ccmm.cz/props/")


class CSVLoader(VocabularyLoader):
    """Load CSV vocabulary files into RDF triplestore."""

    def load(self, uri: str, store: RDFTripleStore) -> int:
        """Load a single CSV file into the triplestore.

        The CSV file should have the following columns:
        - IRI: The concept IRI
        - base IRI: The base IRI for the concept scheme
        - parentId: The parent concept ID (for hierarchical vocabularies)
        - id: The concept identifier
        - title_cs: Czech title
        - title_en: English title
        - definition_cs: Czech definition
        - definition_en: English definition

        Args:
            uri: Location of the CSV file
            store: The RDF triplestore to load data into

        Returns:
            Number of concepts loaded

        """
        csv_path = Path(uri)
        log.info("Loading CSV file: %s", csv_path)

        if not csv_path.exists():
            log.error("CSV file not found: %s", csv_path)
            return 0

        concepts_loaded = 0

        with csv_path.open(encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')

            for csv_row in reader:
                # Clean up whitespace
                row = {key.strip(): value.strip() for key, value in csv_row.items() if key}

                # Extract fields
                iri = row["IRI"].strip()
                base_iri = row["base IRI"].strip()
                parent_id = row.get("parentId", "").strip()
                term_id = row.get("id", "").strip()
                title_cs = row.get("title_cs", "").strip()
                title_en = row.get("title_en", "").strip()
                definition_cs = row.get("definition_cs", "").strip()
                definition_en = row.get("definition_en", "").strip()

                # Skip empty rows
                if not term_id or (not title_cs and not title_en):
                    continue

                # Create concept URI
                concept_uri = URIRef(iri) if iri else URIRef(f"{base_iri}{term_id}")

                # Add concept type
                store.graph.add((concept_uri, RDF.type, SKOS.Concept))

                # Add concept scheme
                scheme_uri = URIRef(base_iri)

                store.graph.add((concept_uri, SKOS.inScheme, scheme_uri))

                # Add labels
                if title_cs:
                    store.graph.add((concept_uri, SKOS.prefLabel, Literal(title_cs, lang="cs")))
                if title_en:
                    store.graph.add((concept_uri, SKOS.prefLabel, Literal(title_en, lang="en")))

                # Add definitions
                if definition_cs:
                    store.graph.add((concept_uri, SKOS.definition, Literal(definition_cs, lang="cs")))
                if definition_en:
                    store.graph.add((concept_uri, SKOS.definition, Literal(definition_en, lang="en")))

                # Add hierarchy relationship
                # When a concept has a parentId, it means this concept is narrower than the parent.
                # Use skos:broader for hierarchical relationships within the same concept scheme.
                # (skos:broader states "the object is broader than the subject")
                if parent_id:
                    parent_uri = URIRef(f"{base_iri}{parent_id}")
                    store.graph.add((concept_uri, SKOS.broader, parent_uri))

                concepts_loaded += 1

        log.info("Loaded %d concepts from %s", concepts_loaded, csv_path.name)
        return concepts_loaded

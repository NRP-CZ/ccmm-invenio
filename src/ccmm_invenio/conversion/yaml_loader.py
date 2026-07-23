#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Load YAML vocabulary data into RDF triplestore."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, SKOS

from ccmm_invenio.conversion.rdf_store import CCMM_MISC, CCMM_PROPS, RDFTripleStore

from .loader import VocabularyLoader

log = logging.getLogger(__name__)


class YAMLLoader(VocabularyLoader):
    """Load YAML vocabulary files into RDF triplestore."""

    def __init__(self, concept_scheme: str) -> None:
        """Initialize the YAML loader.

        Args:
            concept_scheme: URI of the concept scheme
            vocabulary_type: Type of generic vocabulary in invenio

        """
        self.concept_scheme = concept_scheme

    def load(self, uri: str, store: RDFTripleStore) -> int:
        """Load a YAML file into the triplestore.

        Args:
            uri: Path to the YAML file (on the local filesystem)
            store: RDFTripleStore to load into

        Returns:
            Number of concepts loaded

        """
        yaml_path = Path(uri)

        log.info("Loading YAML file: %s", yaml_path)

        # Load YAML data
        with yaml_path.open(encoding="utf-8") as f:
            data = list(yaml.safe_load_all(f))

        # Create concept scheme
        scheme_uri = URIRef(self.concept_scheme)
        store.graph.add((scheme_uri, RDF.type, SKOS.ConceptScheme))

        concepts_loaded = 0

        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                continue

            self._load_single_item(item, scheme_uri, store)
            concepts_loaded += 1

        log.info("Loaded %d concepts from %s", concepts_loaded, yaml_path.name)
        return concepts_loaded

    def _load_single_item(self, item: dict[str, Any], scheme_uri: URIRef, store: RDFTripleStore) -> None:
        """Load a single item from the YAML data into the RDF store."""
        original_id = item["id"]  # Store original case for dc:identifier

        # Create concept URI of the loaded item
        concept_uri = URIRef(f"{scheme_uri}/{original_id}")

        # Add concept type
        store.graph.add((concept_uri, RDF.type, SKOS.Concept))
        store.graph.add((concept_uri, SKOS.inScheme, scheme_uri))

        # Add labels
        if "title" in item:
            titles = item["title"]
            if isinstance(titles, dict):
                self._load_multilingual_string(store, titles, concept_uri, SKOS.prefLabel)

        # Add descriptions
        if "description" in item:
            descriptions = item["description"]
            if isinstance(descriptions, dict):
                self._load_multilingual_string(store, descriptions, concept_uri, SKOS.definition)

        # Add hierarchy (parent relationship)
        if "hierarchy" in item and "parent" in item["hierarchy"]:
            parent_id = item["hierarchy"]["parent"]
            # Use lowercase parent ID to match the child's ID convention
            parent_uri = URIRef(f"{scheme_uri}/{parent_id.lower()}")
            store.graph.add((concept_uri, SKOS.broader, parent_uri))

        # Add custom properties
        if "props" in item:
            props = item["props"]
            if isinstance(props, dict):
                for key, value in props.items():
                    if key == "iri":
                        # Store external IRI for later exactMatch creation
                        # Only if it's different from the NMA namespace
                        external_iri = str(value).rstrip("/")
                        # Make it as an exactMatch to the external IRI
                        store.graph.add((concept_uri, SKOS.exactMatch, Literal(external_iri)))
                    else:
                        # Store acronym as a custom property
                        store.graph.add((concept_uri, CCMM_PROPS.key, Literal(value)))

        # Add icon if present
        if item.get("icon"):
            store.graph.add((concept_uri, CCMM_MISC.icon, Literal(item["icon"])))

        # Add tags if present
        if "tags" in item and isinstance(item["tags"], list):
            for tag in item["tags"]:
                store.graph.add((concept_uri, CCMM_MISC.tag, Literal(tag)))

    def _load_multilingual_string(
        self,
        store: RDFTripleStore,
        multilingual_str: dict[str, Any],
        concept_uri: URIRef,
        predicate: URIRef,
    ) -> None:
        """Load a multilingual string into the RDF store."""
        for lang, val in multilingual_str.items():
            store.graph.add((concept_uri, predicate, Literal(val, lang=lang)))

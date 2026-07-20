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
from typing import TYPE_CHECKING

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS

if TYPE_CHECKING:
    from pathlib import Path

    from ccmm_invenio.conversion.rdf_store import RDFTripleStore

log = logging.getLogger(__name__)

# Namespaces
NMA = Namespace("https://nma.eosc.cz/vocabularies/")
CCMM_PROPS = Namespace("http://vocabs.ccmm.cz/props/")


class YAMLToRDFLoader:
    """Load YAML vocabulary files into RDF triplestore."""

    def __init__(self, store: RDFTripleStore) -> None:
        """Initialize the YAML loader.

        Args:
            store: The RDF triplestore to load data into

        """
        self.store = store

    def load_yaml_file(
        self,
        yaml_path: Path,
        concept_scheme: str,
        vocabulary_type: str,
    ) -> int:
        """Load a YAML file into the triplestore.

        Args:
            yaml_path: Path to the YAML file
            concept_scheme: URI of the concept scheme
            vocabulary_type: Vocabulary type (e.g., "licenses")

        Returns:
            Number of concepts loaded

        """
        import yaml

        log.info("Loading YAML file: %s", yaml_path)

        # Load YAML data
        with yaml_path.open(encoding="utf-8") as f:
            data = list(yaml.safe_load_all(f))

        # Create concept scheme
        scheme_uri = URIRef(concept_scheme)
        self.store.graph.add((scheme_uri, RDF.type, SKOS.ConceptScheme))

        concepts_loaded = 0

        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                continue

            term_id = item["id"]

            # Create concept URI using NMA namespace
            concept_uri = URIRef(f"{NMA}{vocabulary_type}/{term_id}")

            # Add concept type
            self.store.graph.add((concept_uri, RDF.type, SKOS.Concept))
            self.store.graph.add((concept_uri, SKOS.inScheme, scheme_uri))

            # Store the original ID (preserve case) using dc:identifier
            from rdflib.namespace import DC
            self.store.graph.add((concept_uri, DC.identifier, Literal(term_id)))

            # Add labels
            if "title" in item:
                titles = item["title"]
                if isinstance(titles, dict):
                    if "cs" in titles and titles["cs"]:
                        self.store.graph.add(
                            (concept_uri, SKOS.prefLabel, Literal(titles["cs"], lang="cs"))
                        )
                    if "en" in titles and titles["en"]:
                        self.store.graph.add(
                            (concept_uri, SKOS.prefLabel, Literal(titles["en"], lang="en"))
                        )

            # Add descriptions
            if "description" in item:
                descriptions = item["description"]
                if isinstance(descriptions, dict):
                    if "cs" in descriptions and descriptions["cs"]:
                        self.store.graph.add(
                            (concept_uri, SKOS.definition, Literal(descriptions["cs"], lang="cs"))
                        )
                    if "en" in descriptions and descriptions["en"]:
                        self.store.graph.add(
                            (concept_uri, SKOS.definition, Literal(descriptions["en"], lang="en"))
                        )

            # Add hierarchy (parent relationship)
            if "hierarchy" in item and "parent" in item["hierarchy"]:
                parent_id = item["hierarchy"]["parent"]
                parent_uri = URIRef(f"{NMA}{vocabulary_type}/{parent_id}")
                self.store.graph.add((concept_uri, SKOS.broader, parent_uri))

            # Add custom properties
            if "props" in item:
                props = item["props"]
                if isinstance(props, dict):
                    for key, value in props.items():
                        if key == "acronym":
                            # Store acronym as a custom property
                            self.store.graph.add(
                                (concept_uri, CCMM_PROPS.acronym, Literal(value))
                            )
                        elif key == "iri":
                            # Store external IRI for later exactMatch creation
                            # Only if it's different from the NMA namespace
                            external_iri = str(value).rstrip("/")
                            # Store as a temporary property that will be converted to exactMatch
                            self.store.graph.add(
                                (concept_uri, CCMM_PROPS["externalIri"], Literal(external_iri))
                            )
                        # Other props can be added here as needed

            # Add icon if present
            if "icon" in item and item["icon"]:
                self.store.graph.add(
                    (concept_uri, CCMM_PROPS.icon, Literal(item["icon"]))
                )

            # Add tags if present
            if "tags" in item and isinstance(item["tags"], list):
                for tag in item["tags"]:
                    self.store.graph.add(
                        (concept_uri, CCMM_PROPS.tag, Literal(tag))
                    )

            concepts_loaded += 1

        log.info("Loaded %d concepts from %s", concepts_loaded, yaml_path.name)
        return concepts_loaded

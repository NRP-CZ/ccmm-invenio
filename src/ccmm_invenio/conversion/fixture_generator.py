#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Generate Invenio YAML fixtures from RDF triplestore."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .rdf_store import RDFTripleStore

from rdflib import DC, SKOS, Namespace, URIRef

log = logging.getLogger(__name__)

# Define namespaces
SSSOM = Namespace("https://w3id.org/sssom/")
CCMM = Namespace("https://vocabs.ccmm.cz/")
EUVOC = Namespace("http://publications.europa.eu/ontology/euvoc#")
PROPS = Namespace("http://vocabs.ccmm.cz/props/")
CCMM_PROPS = Namespace("http://vocabs.ccmm.cz/props/")


class FixtureGenerator:
    """Generate Invenio fixtures from RDF triplestore."""

    def __init__(self, store: RDFTripleStore) -> None:
        """Initialize the fixture generator."""
        self.store = store
        self.graph = store.graph

    def generate_all(self, output_dir: Path) -> dict[str, int]:
        """Generate all fixtures and return summary of created files."""
        import yaml

        output_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, int] = {}

        # Generate CCMM vocabulary fixtures
        # Note: CCMM scheme URIs have trailing slashes to match CSV base IRIs
        nma_scheme = "https://nma.eosc.cz/vocabularies"

        # Helper function for primary language filter
        def _has_iso_639_1(term: dict[str, Any]) -> bool:
            return term.get("props", {}).get("ISO_639_1") is not None

        generators = [
            (
                "ccmm_agent_roles.yaml",
                self._generate_ccmm_vocabulary,
                f"{nma_scheme}/resourceagentroletypes",
                "resourceagentroletypes",
            ),
            (
                "ccmm_alternate_title_types.yaml",
                self._generate_ccmm_vocabulary,
                f"{nma_scheme}/titletypes",
                "titletypes",
            ),
            (
                "ccmm_location_relation_types.yaml",
                self._generate_ccmm_vocabulary,
                f"{nma_scheme}/locationrelationtypes",
                "locationrelationtypes",
            ),
            (
                "ccmm_relation_types.yaml",
                self._generate_ccmm_vocabulary,
                f"{nma_scheme}/relationtypes",
                "relationtypes",
            ),
            (
                "ccmm_subject_categories.yaml",
                self._generate_ccmm_vocabulary,
                f"{nma_scheme}/subjectcategories",
                "subjectcategories",
            ),
            (
                "ccmm_time_reference_types.yaml",
                self._generate_ccmm_vocabulary,
                f"{nma_scheme}/datetypes",
                "datetypes",
            ),
            ("ccmm_rdm_subjects.yaml", self._generate_rdm_subjects, None, None),
            (
                "ccmm_languages_all.yaml",
                lambda: sorted(
                    self._generate_ccmm_vocabulary(
                        f"{nma_scheme}/languages",
                        extra_props_func=self._get_iso_codes,
                        vocabulary_type="languages",
                    ),
                    key=lambda x: x["id"],
                ),
                None,
                None,
            ),
            (
                "ccmm_languages_primary.yaml",
                lambda: sorted(
                    self._generate_ccmm_vocabulary(
                        f"{nma_scheme}/languages",
                        filter_func=_has_iso_639_1,
                        extra_props_func=self._get_iso_codes,
                        vocabulary_type="languages",
                    ),
                    key=lambda x: x["id"],
                ),
                None,
                None,
            ),
            (
                "ccmm_access_rights.yaml",
                self._generate_ccmm_vocabulary_with_sorting,
                f"{nma_scheme}/accessrights",
                "accessrights",
            ),
            (
                "ccmm_resource_types.yaml",
                self._generate_ccmm_vocabulary_with_sorting,
                f"{nma_scheme}/resourcetypes",
                "resourcetypes",
            ),
            (
                "ccmm_file_types.yaml",
                self._generate_ccmm_vocabulary_with_sorting,
                f"{nma_scheme}/filetypes",
                "filetypes",
            ),
            ("ccmm_contributor_types.yaml", self._generate_contributor_types, None, None),
            (
                "ccmm_licenses.yaml",
                self._generate_ccmm_vocabulary_with_sorting,
                f"{nma_scheme}/licenses",
                "licenses",
            ),
            (
                "ccmm_subject_schemes.yaml",
                self._generate_ccmm_vocabulary_with_sorting,
                f"{nma_scheme}/subjectschemes",
                "subjectschemes",
            ),
        ]

        for filename, generator_func, arg, vocab_type in generators:
            output_path = output_dir / filename
            log.info("Generating %s...", filename)
            try:
                # Call generator with appropriate arguments
                if arg is not None and vocab_type is not None:
                    # For methods that take both scheme and vocab_type
                    data = generator_func(arg, vocabulary_type=vocab_type)
                elif arg is not None:
                    data = generator_func(arg)
                else:
                    data = generator_func()

                # Sort data by ID for stable output
                if isinstance(data, list):
                    data = sorted(data, key=lambda x: str(x.get("id", "")))
                
                # Write to file with sorted keys for stable output
                with output_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        data,
                        f,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=True,
                    )

                results[filename] = len(data)
            except Exception:
                log.exception("Failed to generate %s", filename)
                results[filename] = 0

        return results

    def _generate_ccmm_vocabulary(
        self,
        vocabulary_scheme: str,
        filter_func: Callable[[dict[str, Any]], bool] | None = None,
        extra_props_func: Callable[[URIRef], dict[str, str]] | None = None,
        vocabulary_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate fixture for CCMM vocabularies (agent roles, relations, etc.).

        Args:
            vocabulary_scheme: The full URI of the concept scheme (e.g.,
                "https://vocabs.ccmm.cz/registry/codelist/AgentRole")
            filter_func: Optional filter function to apply to each term
            extra_props_func: Optional function to get extra props for each concept URI
            vocabulary_type: The vocabulary type key from vocabularies.yaml (e.g., "resourceagentroletypes")

        """
        concepts = self._get_ccmm_concepts(vocabulary_scheme)
        sssom_mappings = self._get_sssom_mappings_for_concepts(concepts)

        result = []
        for concept_uri in self._sort_by_hierarchy(concepts):
            extra_props = extra_props_func(concept_uri) if extra_props_func else None
            term = self._build_term(
                concept_uri,
                sssom_mappings,
                extra_props=extra_props,
                vocabulary_type=vocabulary_type,
            )
            if term and (filter_func is None or filter_func(term)):
                result.append(term)

        return result

    def _generate_rdm_subjects(self) -> list[dict[str, Any]]:
        """Generate RDM subjects fixture (special format for Invenio subjects)."""
        concepts = self._get_ccmm_concepts("https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/")
        result = []

        for concept_uri in concepts:
            labels = self._get_labels(concept_uri)
            if not labels["en"] and not labels["cs"]:
                continue

            concept_str = str(concept_uri)
            term_id = self._extract_id_from_uri(concept_uri)

            # Create NMA IRI
            new_iri = f"https://nma.eosc.cz/vocabularies/subjects/{term_id}"

            # Extract old namespace and ID path for exactMatch
            old_namespace = self._get_namespace_uri(concept_str)
            props: dict[str, Any] = {"iri": new_iri}

            if old_namespace:
                old_id_path = concept_str[len(old_namespace) :].rstrip("/")
                if old_id_path:
                    prop_key = f"skos:exactMatch:{old_namespace.rstrip('/')}"
                    props[prop_key] = old_id_path

            term: dict[str, Any] = {
                "id": term_id,
                "scheme": "frascati",
                "subject": labels["en"] or labels["cs"],
                "title": {
                    "cs": labels["cs"] or labels["en"],
                    "en": labels["en"] or labels["cs"],
                },
                "props": props,
            }

            result.append(term)

        return result

    def _generate_contributor_types(self) -> list[dict[str, Any]]:
        """Generate contributor types (descendants of AgentRole/Contributor)."""
        # Get all agent roles first with the correct vocabulary type
        agent_roles = self._generate_ccmm_vocabulary(
            "https://vocabs.ccmm.cz/registry/codelist/AgentRole/",
            vocabulary_type="contributorsroles",
        )

        # Find the Contributor concept by its new IRI
        contributor_new_iri = "https://nma.eosc.cz/vocabularies/contributorsroles/contributor"
        contributor_id = None
        for term in agent_roles:
            if term.get("props", {}).get("iri") == contributor_new_iri:
                contributor_id = term["id"]
                break

        if not contributor_id:
            log.warning("Contributor concept not found in AgentRole")
            return []

        # Filter descendants
        return self._filter_descendants(agent_roles, {contributor_id})

    def _get_ccmm_concepts(self, scheme_uri: str) -> list:
        """Get all concepts for a CCMM vocabulary by scheme URI.

        Args:
            scheme_uri: The full URI of the concept scheme (e.g.,
                "https://vocabs.ccmm.cz/registry/codelist/AgentRole")

        """
        return self._get_concepts_by_scheme(scheme_uri)

    def _get_concepts_by_scheme(self, scheme_uri: str) -> list:
        """Get all concepts belonging to a specific concept scheme.

        Args:
            scheme_uri: The full URI of the concept scheme.

        Returns:
            List of concept URIs belonging to the scheme.

        """
        query = (
            f"SELECT DISTINCT ?concept WHERE {{  ?concept a skos:Concept ;           skos:inScheme <{scheme_uri}> .}}"
        )
        results = self.graph.query(query)
        return [row[0] for row in results]

    def _generate_ccmm_vocabulary_with_sorting(
        self, scheme_uri: str, vocabulary_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Generate vocabulary fixtures with hierarchical sorting.

        This is a convenience method for vocabularies that need parent-first ordering.

        Args:
            scheme_uri: The full URI of the concept scheme.
            vocabulary_type: The vocabulary type key from vocabularies.yaml

        Returns:
            List of term dictionaries sorted by hierarchy.

        """
        concepts = self._get_concepts_by_scheme(scheme_uri)
        sssom_mappings = self._get_sssom_mappings_for_concepts(concepts)

        result = []
        for concept_uri in self._sort_by_hierarchy(concepts):
            term = self._build_term(
                concept_uri,
                sssom_mappings,
                vocabulary_type=vocabulary_type,
            )
            if term:
                result.append(term)

        return result

    def _get_sssom_mappings_for_concepts(self, concepts: list) -> dict[str, dict[tuple[str, str], set[str]]]:
        """Get SSSOM mappings for a list of concepts.

        Returns mappings where keys are concept URIs and values are dicts mapping
        (predicate, namespace_uri) tuples to sets of IDs within those namespaces.
        The predicate is the short form like 'skos:exactMatch'.
        """
        mappings: dict[str, dict[tuple[str, str], set[str]]] = defaultdict(lambda: defaultdict(set))

        for concept in concepts:
            concept_str = str(concept)

            # Query for mappings where concept is the target (object)
            # This is for COAR/CCMM concepts that are mapped TO from external systems
            query_as_target = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT ?source ?predicate WHERE {{
                ?annotation owl:annotatedSource ?source ;
                           owl:annotatedTarget <{concept_str}> ;
                           owl:annotatedProperty ?predicate .
            }}
            """
            for row in self.graph.query(query_as_target):
                source_uri = str(row[0])
                predicate_uri = str(row[1])
                # Convert predicate URI to short form (e.g., skos:exactMatch)
                predicate_short = self._get_predicate_short_form(predicate_uri)
                # Use namespace URI + id pattern instead of explicit system names
                namespace_uri = self._get_namespace_uri(source_uri)
                if namespace_uri and predicate_short:
                    # Extract the full ID path (everything after the namespace)
                    id_path = source_uri[len(namespace_uri) :].rstrip("/")
                    mappings[concept_str][(predicate_short, namespace_uri)].add(id_path)

            # Query for mappings where concept is the source
            # This is for external concepts that map TO COAR/CCMM
            query_as_source = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            SELECT ?target ?predicate WHERE {{
                ?annotation owl:annotatedSource <{concept_str}> ;
                           owl:annotatedTarget ?target ;
                           owl:annotatedProperty ?predicate .
            }}
            """
            for row in self.graph.query(query_as_source):
                target_uri = str(row[0])
                predicate_uri = str(row[1])
                # Convert predicate URI to short form (e.g., skos:exactMatch)
                predicate_short = self._get_predicate_short_form(predicate_uri)
                # Use namespace URI + id pattern instead of explicit system names
                namespace_uri = self._get_namespace_uri(target_uri)
                if namespace_uri and predicate_short:
                    # Extract the full ID path (everything after the namespace)
                    id_path = target_uri[len(namespace_uri) :].rstrip("/")
                    mappings[concept_str][(predicate_short, namespace_uri)].add(id_path)

        return mappings

    def _get_predicate_short_form(self, predicate_uri: str) -> str | None:
        """Convert a predicate URI to its short form (e.g., skos:exactMatch).

        Args:
            predicate_uri: Full URI of the predicate

        Returns:
            Short form like 'skos:exactMatch', or None if not recognized

        """
        # Define known SKOS and OWL predicates
        known_predicates = {
            str(SKOS.exactMatch): "skos:exactMatch",
            str(SKOS.closeMatch): "skos:closeMatch",
            str(SKOS.broadMatch): "skos:broadMatch",
            str(SKOS.narrowMatch): "skos:narrowMatch",
            str(SKOS.relatedMatch): "skos:relatedMatch",
            "http://www.w3.org/2002/07/owl#sameAs": "owl:sameAs",
        }
        return known_predicates.get(predicate_uri)

    def _get_namespace_uri(self, uri: str) -> str | None:
        """Extract namespace URI from a full concept URI.

        For example, given:
          https://schema.datacite.org/meta/kernel-4/creator
        returns:
          https://schema.datacite.org/meta/kernel-4/

        For hierarchical vocabularies like SubjectCategory, extracts the base namespace:
          https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/10000/10100/10103
        returns:
          https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/
        """
        # Remove trailing slash if present for consistent processing
        uri = uri.rstrip("/")

        # Special handling for known hierarchical vocabularies
        # These use numeric hierarchical paths after the base codelist name
        hierarchical_bases = [
            "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory",
            "https://vocabs.ccmm.cz/registry/codelist/ResourceType",
            "https://vocabs.ccmm.cz/registry/codelist/ResourceAgentRoleType",
        ]

        for base in hierarchical_bases:
            if uri.startswith(base):
                # Return the base with trailing slash
                return base + "/"

        # For non-hierarchical URIs, find the last slash and include it to get the namespace
        last_slash_idx = uri.rfind("/")
        if last_slash_idx > 0:
            # Return namespace with trailing slash
            return uri[: last_slash_idx + 1]
        return None

    def _build_term(
        self,
        concept_uri: URIRef,
        sssom_mappings: dict[str, dict[tuple[str, str], set[str]]],
        extra_props: dict[str, str] | None = None,
        vocabulary_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Build a term dictionary from RDF data.

        Args:
            concept_uri: The concept URI
            sssom_mappings: Existing SSSOM mappings
            extra_props: Additional properties to add
            vocabulary_type: The vocabulary type key from vocabularies.yaml (e.g., "resourceagentroletypes")

        """
        labels = self._get_labels(concept_uri)
        descriptions = self._get_descriptions(concept_uri)

        # Skip if no labels
        if not labels["en"] and not labels["cs"]:
            return None

        concept_str = str(concept_uri)
        term_id = self._extract_id_from_uri(concept_uri)

        # Determine the new standardized IRI and old namespace mapping
        new_iri = concept_str
        old_namespace = None
        old_id_path = None

        if vocabulary_type:
            # Extract the namespace from the concept IRI
            old_namespace = self._get_namespace_uri(concept_str)
            if old_namespace:
                # Get the path after the namespace (for the exactMatch mapping)
                old_id_path = concept_str[len(old_namespace) :].rstrip("/")
                # Construct new standardized IRI using vocabulary type and term_id
                new_iri = f"https://nma.eosc.cz/vocabularies/{vocabulary_type}/{term_id}"

        term: dict[str, Any] = {
            "id": term_id,
            "title": {
                "cs": labels["cs"] or labels["en"],
                "en": labels["en"] or labels["cs"],
            },
        }

        # Add descriptions if present
        if descriptions["cs"] or descriptions["en"]:
            term["description"] = {}
            if descriptions["cs"]:
                term["description"]["cs"] = descriptions["cs"]
            if descriptions["en"]:
                term["description"]["en"] = descriptions["en"]

        # Build props
        props: dict[str, Any] = {"iri": new_iri}

        # Add old IRI namespace as skos:exactMatch if we created a new IRI from an external source
        # Don't add exactMatch if the old namespace is already NMA (YAML-sourced vocabularies)
        nma_namespace = f"https://nma.eosc.cz/vocabularies/{vocabulary_type}/" if vocabulary_type else None
        if old_namespace and old_id_path and new_iri != concept_str:
            # Only add if old namespace is not the NMA namespace
            if old_namespace != nma_namespace:
                prop_key = f"skos:exactMatch:{old_namespace.rstrip('/')}"
                props[prop_key] = old_id_path

        # Add SSSOM mappings using predicate:namespaceURI format
        if concept_str in sssom_mappings:
            for (predicate, namespace_uri), ids in sssom_mappings[concept_str].items():
                if ids:
                    # Create property key as "predicate:namespace" (without trailing slash)
                    prop_key = f"{predicate}:{namespace_uri.rstrip('/')}"
                    # Join multiple IDs with comma
                    props[prop_key] = ", ".join(sorted(ids))

        # Add all CCMM_PROPS properties dynamically (except externalIri which is handled below)
        ccmm_props = self._get_ccmm_props(concept_uri)
        props.update(ccmm_props)

        # Handle external IRI (from YAML vocabularies) and convert to exactMatch
        # Query for externalIri separately since it's filtered out by _get_ccmm_props
        for obj in self.graph.objects(concept_uri, CCMM_PROPS.externalIri):
            external_iri = str(obj)
            # Extract namespace from external IRI
            namespace_uri = self._get_namespace_uri(external_iri)
            if namespace_uri:
                # Get the ID path (everything after namespace)
                id_path = external_iri[len(namespace_uri) :].rstrip("/")
                if id_path:  # Only add if there's an ID
                    prop_key = f"skos:exactMatch:{namespace_uri.rstrip('/')}"
                    props[prop_key] = id_path
                # If no ID (URL ends with just namespace), don't add exactMatch
                # as it doesn't make sense without an identifier

        # Handle skos:exactMatch triples (added e.g. by create_nma_vocabulary_terms
        # when a concept was created in an NMA scheme from an external source)
        for obj in self.graph.objects(concept_uri, SKOS.exactMatch):
            match_iri = str(obj)
            namespace_uri = self._get_namespace_uri(match_iri)
            if namespace_uri:
                id_path = match_iri[len(namespace_uri) :].rstrip("/")
                if id_path:
                    prop_key = f"skos:exactMatch:{namespace_uri.rstrip('/')}"
                    props[prop_key] = id_path

        # Add extra properties (for backward compatibility)
        if extra_props:
            props.update(extra_props)

        term["props"] = props

        # Add hierarchy if present
        broader = self._get_broader(concept_uri)
        if broader:
            parent_id = self._extract_id_from_uri(broader)
            term["hierarchy"] = {"parent": parent_id}

        # Add icon if present in props
        if "icon" in props:
            term["icon"] = props.pop("icon")

        # Add tags if present in props (as a list)
        tags = []
        for pred, obj in self.graph.predicate_objects(concept_uri):
            if str(pred) == f"{CCMM_PROPS}tag":
                tags.append(str(obj))
        if tags:
            term["tags"] = tags
            # Remove individual tag props
            props.pop("tag", None)

        return term

    def _get_labels(self, concept_uri: URIRef) -> dict[str, str]:
        """Get labels in different languages."""
        labels = {"cs": "", "en": ""}

        # Try prefLabel first
        for lang in ["cs", "en"]:
            for obj in self.graph.objects(concept_uri, SKOS.prefLabel):
                if obj.language == lang:
                    labels[lang] = str(obj)
                    break

        # Fallback to altLabel for English if no prefLabel
        if not labels["en"]:
            for obj in self.graph.objects(concept_uri, SKOS.altLabel):
                if obj.language == "en":
                    labels["en"] = str(obj)
                    break

        # If still no English, use any prefLabel without language tag
        if not labels["en"]:
            for obj in self.graph.objects(concept_uri, SKOS.prefLabel):
                if not obj.language:
                    labels["en"] = str(obj)
                    break

        return labels

    def _get_descriptions(self, concept_uri: URIRef) -> dict[str, str]:
        """Get descriptions in different languages."""
        descriptions = {"cs": "", "en": ""}

        for lang in ["cs", "en"]:
            for obj in self.graph.objects(concept_uri, SKOS.definition):
                if obj.language == lang:
                    descriptions[lang] = str(obj)
                    break

        return descriptions

    def _get_broader(self, concept_uri: URIRef) -> URIRef | None:
        """Get broader concept (parent)."""
        # First try skos:broader
        for obj in self.graph.objects(concept_uri, SKOS.broader):
            return obj

        # Then try skos:broadMatch
        for obj in self.graph.objects(concept_uri, SKOS.broadMatch):
            return obj

        return None

    def _extract_id_from_uri(self, uri: URIRef) -> str:
        """Extract ID from URI (always lowercase).

        For concepts with dc:identifier, uses it but lowercases the result.
        For other concepts, extracts from URI and lowercases it.
        """
        uri_str = str(uri)

        # Try dc:identifier first (but always lowercase for consistency)
        for obj in self.graph.objects(uri, DC.identifier):
            return str(obj).lower()

        # Otherwise extract from URI and lowercase it
        return uri_str.rstrip("/").split("/")[-1].lower()

    def _get_iso_codes(self, concept_uri: URIRef) -> dict[str, str]:
        """Get ISO language codes from both skos:notation and ccmm_props."""
        codes = {}

        # Query for ISO codes from skos:notation (original approach)
        query = f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?notation ?datatype WHERE {{
            <{concept_uri}> skos:notation ?notation .
            BIND(DATATYPE(?notation) AS ?datatype)
        }}
        """
        for row in self.graph.query(query):
            notation = str(row[0])
            datatype = str(row[1])

            if "ISO_639_1" in datatype:
                codes["ISO_639_1"] = notation
            elif "ISO_639_2T" in datatype:
                codes["ISO_639_2T"] = notation
            elif "ISO_639_2B" in datatype:
                codes["ISO_639_2B"] = notation
            elif "ISO_639_3" in datatype:
                codes["ISO_639_3"] = notation
            elif "XML_LNG" in datatype:
                codes["XML_LNG"] = notation

        # Get all ccmm_props properties dynamically
        ccmm_props_codes = self._get_ccmm_props(concept_uri)
        codes.update(ccmm_props_codes)

        return codes

    def _get_ccmm_props(self, concept_uri: URIRef) -> dict[str, str]:
        """Get all properties in the CCMM_PROPS namespace for a concept.

        Args:
            concept_uri: The concept URI

        Returns:
            Dictionary mapping property names to their values

        """
        props = {}

        # Query for all properties in the CCMM_PROPS namespace
        ccmm_props_prefix = str(CCMM_PROPS)
        for pred, obj in self.graph.predicate_objects(concept_uri):
            pred_str = str(pred)
            # Check if the predicate is in the CCMM_PROPS namespace
            if pred_str.startswith(ccmm_props_prefix):
                # Extract the property name (everything after the namespace)
                prop_name = pred_str[len(ccmm_props_prefix) :]
                # Skip baseIri as it's redundant with the concept URI
                # Also skip externalIri as it's handled separately in _build_term
                if prop_name not in ("baseIri", "externalIri"):
                    props[prop_name] = str(obj)

        return props

    def _sort_by_hierarchy(self, concepts: list) -> list:
        """Sort concepts so parents come before children."""
        sorted_concepts = []
        sorted_ids = set()

        # Build hierarchy map
        hierarchy_map: dict[str, str] = {}
        for concept in concepts:
            broader = self._get_broader(concept)
            if broader:
                hierarchy_map[str(concept)] = str(broader)

        # First pass: add concepts without parents
        remaining = list(concepts)
        while remaining:
            to_add = []
            still_remaining = []

            for concept in remaining:
                concept_str = str(concept)
                parent = hierarchy_map.get(concept_str)

                if not parent or parent in sorted_ids or parent not in [str(c) for c in concepts]:
                    to_add.append(concept)
                    sorted_ids.add(concept_str)
                else:
                    still_remaining.append(concept)

            if not to_add and still_remaining:
                # Break circular dependencies
                to_add = [still_remaining[0]]
                sorted_ids.add(str(still_remaining[0]))
                still_remaining = still_remaining[1:]

            sorted_concepts.extend(to_add)
            remaining = still_remaining

        return sorted_concepts

    def _filter_descendants(self, items: list[dict[str, Any]], ancestor_ids: set[str]) -> list[dict[str, Any]]:
        """Filter items to only include descendants of specified ancestors."""
        known_parents = set(ancestor_ids)
        result = []

        # Multiple passes to handle nested hierarchies
        max_iterations = 100
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            found_new = False

            for item in items:
                if item["id"] in known_parents or item["id"] in [r["id"] for r in result]:
                    continue

                parent = item.get("hierarchy", {}).get("parent")
                if parent and parent in known_parents:
                    result.append(item)
                    known_parents.add(item["id"])
                    found_new = True

            if not found_new:
                break

        # Clean up hierarchy references for items not in result
        result_ids = {item["id"] for item in result}
        for item in result:
            if "hierarchy" in item:
                parent = item["hierarchy"]["parent"]
                if parent not in result_ids:
                    del item["hierarchy"]

        return result

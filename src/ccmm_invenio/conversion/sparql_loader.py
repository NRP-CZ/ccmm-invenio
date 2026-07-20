#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Load vocabulary data from SPARQL endpoints into RDF triplestore."""

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from rdflib import RDF, SKOS, Graph, Literal, URIRef
from tenacity import (  # type: ignore[reportMissingImports]
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm.contrib.concurrent import process_map  # type: ignore[reportMissingImports]

if TYPE_CHECKING:
    from ccmm_invenio.conversion.rdf_store import RDFTripleStore

log = logging.getLogger(__name__)

# Retry configuration for network requests
RETRY_CONFIG = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, min=2, max=30),
    "retry": retry_if_exception_type((URLError, HTTPError, ConnectionError)),
    "before_sleep": before_sleep_log(log, logging.WARNING),
    "reraise": True,
}


@retry(**RETRY_CONFIG)
def fetch_rdf_from_url(
    url: str,
    format: str = "xml",  # noqa: A002
) -> Graph:
    """Fetch RDF data from a URL with automatic retries.

    Args:
        url: The URL to fetch RDF data from
        format: The RDF format (xml, turtle, n3, etc.)

    Returns:
        RDF Graph

    Raises:
        Exception: If fetching fails after retries

    """
    log.debug("Fetching RDF from %s (format: %s)", url, format)
    graph = Graph()
    try:
        graph.parse(url, format=format)
    except Exception as e:
        log.warning("Attempt failed for %s: %s", url, e)
        raise
    else:
        log.info("Successfully fetched %d triples from %s", len(graph), url)
        return graph


class SPARQLLoader:
    """Load vocabulary data from SPARQL endpoints or RDF files."""

    def __init__(self, store: RDFTripleStore) -> None:
        """Initialize the SPARQL loader.

        Args:
            store: The RDF triplestore to load data into

        """
        self.store = store

    @retry(**RETRY_CONFIG)
    def _query_sparql_endpoint(
        self,
        endpoint: str,
        query: str,
    ) -> list[dict[str, str]]:
        """Query a SPARQL endpoint and return results with automatic retries.

        Args:
            endpoint: SPARQL endpoint URL
            query: SPARQL query string

        Returns:
            List of result bindings as dictionaries

        Raises:
            Exception: If query fails after retries

        """
        params = {"query": query}
        request = Request(
            endpoint,
            data=urlencode(params).encode("utf-8"),
            headers={"Accept": "application/sparql-results+xml"},
        )

        with urlopen(request, timeout=120) as response:
            xml_data = response.read()

        # Parse SPARQL XML results
        return self._parse_sparql_xml_results(xml_data)

    def _parse_sparql_xml_results(self, xml_data: bytes) -> list[dict[str, str]]:
        """Parse SPARQL XML results into a list of binding dictionaries.

        Args:
            xml_data: XML data from SPARQL endpoint

        Returns:
            List of result bindings as dictionaries

        """
        root = ElementTree.fromstring(xml_data)
        ns = {"sparql": "http://www.w3.org/2005/sparql-results#"}

        results = []
        for result in root.findall(".//sparql:result", ns):
            binding_dict = self._parse_sparql_binding(result, ns)
            if binding_dict:
                results.append(binding_dict)

        return results

    def _parse_sparql_binding(
        self,
        result_elem: ElementTree.Element,
        ns: dict[str, str],
    ) -> dict[str, dict[str, str]]:
        """Parse a single SPARQL result binding.

        Args:
            result_elem: XML element containing the result
            ns: XML namespace mappings

        Returns:
            Dictionary of variable bindings

        """
        binding_dict = {}
        for binding in result_elem.findall(".//sparql:binding", ns):
            var_name = binding.get("name")
            uri_elem = binding.find(".//sparql:uri", ns)
            literal_elem = binding.find(".//sparql:literal", ns)

            if uri_elem is not None and uri_elem.text:
                binding_dict[var_name] = {"type": "uri", "value": uri_elem.text}
            elif literal_elem is not None and literal_elem.text:
                lang = literal_elem.get("{http://www.w3.org/XML/1998/namespace}lang")
                binding_dict[var_name] = {
                    "type": "literal",
                    "value": literal_elem.text,
                    "lang": lang,
                }

        return binding_dict

    def _build_concept_query(self, scheme_uri: str, limit: int, offset: int) -> str:
        """Build a SPARQL query for fetching concepts with properties.

        Args:
            scheme_uri: Concept scheme URI
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            SPARQL query string

        """
        return f"""
            SELECT DISTINCT ?concept ?prefLabel ?definition ?altLabel
            WHERE {{
                ?concept a skos:Concept ;
                         skos:inScheme <{scheme_uri}> .
                OPTIONAL {{ ?concept skos:prefLabel ?prefLabel }}
                OPTIONAL {{ ?concept skos:definition ?definition }}
                OPTIONAL {{ ?concept skos:altLabel ?altLabel }}
            }}
            ORDER BY ?concept
            LIMIT {limit}
            OFFSET {offset}
        """

    def _add_triple_to_graph(
        self,
        graph: Graph,
        concept_uri: URIRef,
        predicate: URIRef,
        result_data: dict[str, str] | None,
    ) -> None:
        """Add a triple to the graph if result data is valid.

        Args:
            graph: RDF graph to add to
            concept_uri: Subject URI
            predicate: Predicate URI
            result_data: Dictionary with 'type', 'value', and optional 'lang'

        """
        if not result_data or result_data["type"] != "literal":
            return

        value = result_data.get("value")
        if not value:
            return

        lang = result_data.get("lang")
        if lang:
            graph.add((concept_uri, predicate, Literal(value, lang=lang)))
        else:
            graph.add((concept_uri, predicate, Literal(value)))

    def _process_sparql_result(
        self,
        graph: Graph,
        result: dict[str, dict[str, str]],
        scheme_uri: str,
    ) -> None:
        """Process a single SPARQL result and add triples to the graph.

        Args:
            graph: RDF graph to add to
            result: SPARQL result binding
            scheme_uri: Concept scheme URI

        """
        concept = result.get("concept")
        if not concept or concept["type"] != "uri":
            return

        concept_uri = URIRef(concept["value"])

        # Add concept type and scheme
        graph.add((concept_uri, RDF.type, SKOS.Concept))
        graph.add((concept_uri, SKOS.inScheme, URIRef(scheme_uri)))

        # Add labels and definitions
        self._add_triple_to_graph(graph, concept_uri, SKOS.prefLabel, result.get("prefLabel"))
        self._add_triple_to_graph(graph, concept_uri, SKOS.definition, result.get("definition"))
        self._add_triple_to_graph(graph, concept_uri, SKOS.altLabel, result.get("altLabel"))

    def _fetch_page(
        self,
        endpoint: str,
        scheme_uri: str,
        page_size: int,
        offset: int,
        page_num: int,
    ) -> list[dict[str, dict[str, str]]]:
        """Fetch a single page of results from the SPARQL endpoint.

        Args:
            endpoint: SPARQL endpoint URL
            scheme_uri: Concept scheme URI
            page_size: Number of results per page
            offset: Result offset
            page_num: Page number (for logging)

        Returns:
            List of SPARQL result bindings

        """
        log.info("Fetching page %d (offset: %d, limit: %d)", page_num, offset, page_size)
        query = self._build_concept_query(scheme_uri, page_size, offset)
        results = self._query_sparql_endpoint(endpoint, query)
        log.info("Received %d results in page %d", len(results), page_num)
        return results

    def _load_subgraphs(self, graph: Graph, scheme_uri: str, format: str = "xml") -> None:
        """Load all subgraphs from the SKOS concept scheme and merge them into the graph.

        This downloads each individual concept URI to get full details (labels, etc.).

        Args:
            graph: Graph to enrich with subgraph data
            scheme_uri: Concept scheme URI
            format: RDF format to use when fetching subgraphs

        """
        log.info("Loading subgraphs for concepts in %s...", scheme_uri)

        # Get all concepts from the scheme
        scheme = URIRef(scheme_uri)
        subjects = [str(x) for x in graph.subjects(SKOS.inScheme, scheme)]
        log.info("Found %d concepts to load subgraphs for", len(subjects))

        # Load all subgraphs in parallel using partial to bind the format parameter
        for subject_graph in process_map(
            partial(fetch_rdf_from_url, format=format),
            subjects,
            max_workers=20,
            chunksize=10,
            leave=False,
            unit="subgraph",
            desc="Loading subgraphs",
        ):
            graph += cast(Graph, subject_graph)

        log.info("Finished loading subgraphs, graph now has %d triples", len(graph))

    def _extract_extra_properties(
        self,
        graph: Graph,
        scheme_uri: str,
        extra_props: dict[str, str],
        prefixes: dict[str, str],
    ) -> Graph:
        """Extract extra properties from concepts using SPARQL queries.

        Args:
            graph: Source graph to query
            scheme_uri: Concept scheme URI
            extra_props: Dictionary mapping property names to SPARQL query patterns
            prefixes: Dictionary mapping prefix names to namespace URIs

        Returns:
            Graph with extracted properties using CCMM_PROPS namespace

        """
        from rdflib import Namespace

        CCMM_PROPS = Namespace("http://vocabs.ccmm.cz/props/")

        log.info("Extracting extra properties for scheme %s...", scheme_uri)

        # Build prefix declarations for the query
        prefix_decls = "\n".join(f"PREFIX {key}: <{value}>" for key, value in prefixes.items())

        # Build OPTIONAL clauses for extra properties
        optional_clauses = "\n".join(f"OPTIONAL {{ {query} }}" for query in extra_props.values())

        # Build variable list
        var_list = " ".join(f"?{key}" for key in extra_props.keys())

        # Construct the full query
        query = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            {prefix_decls}

            SELECT ?concept {var_list}
            WHERE {{
                ?concept a skos:Concept ;
                         skos:inScheme <{scheme_uri}> .
                {optional_clauses}
            }}
        """

        log.debug("Extra properties query: %s", query)

        # Execute query
        results = list(graph.query(query))
        log.info("Found %d results with extra properties", len(results))

        # Build result graph with CCMM_PROPS namespace
        result_graph = Graph()
        result_graph.bind("ccmm_props", CCMM_PROPS)

        for row in results:
            concept_uri = row[0]
            if not concept_uri:
                continue

            # Add each extra property as ccmm_props:PropertyName
            for i, prop_name in enumerate(extra_props.keys()):
                value = row[i + 1]  # +1 because concept is first
                if value:
                    # Create property URI in CCMM_PROPS namespace
                    prop_uri = CCMM_PROPS[prop_name]
                    result_graph.add((concept_uri, prop_uri, value))

        log.info("Extracted %d property triples", len(result_graph))
        return result_graph

    def load_from_sparql_endpoint(
        self,
        endpoint: str,
        scheme_uri: str,
        load_subgraphs: bool = False,
        format: str = "xml",
        extra_props: dict[str, str] | None = None,
        prefixes: dict[str, str] | None = None,
    ) -> int:
        """Load concepts with labels from an RDF source.

        This method downloads the RDF data locally first, then queries it,
        which is more efficient than paginated remote queries.

        Args:
            endpoint: RDF file URL
            scheme_uri: Concept scheme URI to query
            load_subgraphs: Whether to load individual concept URIs for full details
            format: RDF format (default: xml)
            extra_props: Dictionary mapping property names to SPARQL query patterns
            prefixes: Dictionary mapping prefix names to namespace URIs

        Returns:
            Number of triples added

        """
        log.info("Loading RDF data for scheme: %s", scheme_uri)

        try:
            # Download the entire RDF graph locally
            log.info("Downloading RDF graph from %s...", endpoint)
            graph = Graph()
            graph.parse(endpoint, format=format)
            log.info("Downloaded %d triples from %s", len(graph), endpoint)

            # Enrich the graph with missing skos:Concept types
            graph = self._enrich_graph(graph)

            # Optionally load subgraphs (individual concept URIs)
            if load_subgraphs:
                self._load_subgraphs(graph, scheme_uri, format=format)

            # Extract extra properties if specified
            if extra_props and prefixes:
                extra_graph = self._extract_extra_properties(
                    graph, scheme_uri, extra_props, prefixes
                )
                graph += extra_graph

            # Query locally for concepts with labels
            query = f"""
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                PREFIX dc: <http://purl.org/dc/elements/1.1/>
                
                SELECT DISTINCT ?concept ?prefLabel ?definition ?altLabel
                WHERE {{
                    ?concept a skos:Concept ;
                             skos:inScheme <{scheme_uri}> .
                    OPTIONAL {{ ?concept skos:prefLabel ?prefLabel }}
                    OPTIONAL {{ ?concept skos:definition ?definition }}
                    OPTIONAL {{ ?concept skos:altLabel ?altLabel }}
                }}
                ORDER BY ?concept
            """

            log.info("Querying local graph for concepts in scheme %s...", scheme_uri)
            results = list(graph.query(query))
            log.info("Found %d concept-property combinations", len(results))

            # Build enriched graph from query results
            enriched_graph = Graph()
            for row in results:
                concept_uri = row[0]
                pref_label = row[1]
                definition = row[2]
                alt_label = row[3]

                # Add concept type and scheme
                enriched_graph.add((concept_uri, RDF.type, SKOS.Concept))
                enriched_graph.add((concept_uri, SKOS.inScheme, URIRef(scheme_uri)))

                # Add prefLabel
                if pref_label:
                    enriched_graph.add((concept_uri, SKOS.prefLabel, pref_label))

                # Add definition
                if definition:
                    enriched_graph.add((concept_uri, SKOS.definition, definition))

                # Add altLabel
                if alt_label:
                    enriched_graph.add((concept_uri, SKOS.altLabel, alt_label))

            # Add extra properties to the enriched graph
            if extra_props and prefixes:
                # Query for extra properties from the full graph
                extra_query_graph = self._extract_extra_properties(
                    graph, scheme_uri, extra_props, prefixes
                )
                enriched_graph += extra_query_graph

            # Merge into store
            before_count = self.store.size()
            self.store.merge(enriched_graph)
            after_count = self.store.size()
            added = after_count - before_count

            log.info("Added %d triples from RDF source for %s", added, scheme_uri)
            return added

        except Exception:
            log.exception("Failed to load from RDF source")
            return 0

    def _enrich_graph(self, graph: Graph) -> Graph:
        """Enrich the graph by adding missing SKOS metadata.

        Some vocabularies (e.g., EU Publications Office) don't explicitly
        declare their concepts with rdf:type skos:Concept, but they do have
        skos:inScheme properties. This method adds the missing type declarations.

        Args:
            graph: The RDF graph to enrich

        Returns:
            The enriched graph (modified in place)

        """
        # Find all resources that have skos:inScheme but are not typed as skos:Concept
        resources_with_scheme = set(graph.subjects(SKOS.inScheme, None))
        typed_concepts = set(graph.subjects(RDF.type, SKOS.Concept))

        # Add skos:Concept type to resources that have skos:inScheme but no type
        missing_type = resources_with_scheme - typed_concepts

        if missing_type:
            log.info("Adding skos:Concept type to %d resources with skos:inScheme", len(missing_type))
            for resource in missing_type:
                graph.add((resource, RDF.type, SKOS.Concept))

        return graph

    def load_from_url(
        self,
        url: str,
        format: str = "xml",  # noqa: A002
        enrich: bool = True,
    ) -> int:
        """Load RDF data from a URL.

        Args:
            url: The URL to load data from
            format: The RDF format (xml, turtle, n3, nt, etc.)
            enrich: Whether to enrich the graph with missing metadata

        Returns:
            Number of triples loaded

        """
        log.info("Loading RDF data from URL: %s", url)

        try:
            graph = fetch_rdf_from_url(url, format=format)

            # Enrich the graph with missing metadata
            if enrich:
                graph = self._enrich_graph(graph)

            before_count = self.store.size()
            self.store.merge(graph)
            after_count = self.store.size()
            added = after_count - before_count

            log.info("Loaded %d triples from %s", added, url)
        except Exception:
            log.exception("Failed to load RDF from URL: %s", url)
            return 0
        else:
            return added

    def load_from_file(
        self,
        file_path: Path,
        format: str = "turtle",  # noqa: A002
        enrich: bool = True,
    ) -> int:
        """Load RDF data from a local file.

        Args:
            file_path: Path to the RDF file
            format: The RDF format (turtle, xml, n3, nt, etc.)
            enrich: Whether to enrich the graph with missing metadata

        Returns:
            Number of triples loaded

        """
        log.info("Loading RDF data from file: %s", file_path)

        if not file_path.exists():
            log.error("File not found: %s", file_path)
            return 0

        try:
            graph = Graph()
            with file_path.open(encoding="utf-8") as f:
                graph.parse(f, format=format)

            # Enrich the graph with missing metadata
            if enrich:
                graph = self._enrich_graph(graph)

            before_count = self.store.size()
            self.store.merge(graph)
            after_count = self.store.size()
            added = after_count - before_count

            log.info("Loaded %d triples from %s", added, file_path.name)
        except Exception:
            log.exception("Failed to load RDF from file: %s", file_path)
            return 0
        else:
            return added

    def load_vocabulary_source(
        self,
        source: str | Path,
        format: str = "xml",  # noqa: A002
        load_subgraphs: bool = False,
        enrich: bool = True,
    ) -> int:
        """Load a vocabulary source (URL or file path).

        Args:
            source: URL or file path to load from
            format: The RDF format
            load_subgraphs: If True, will also load related subgraphs (for distributed vocabularies)
            enrich: Whether to enrich the graph with missing metadata

        Returns:
            Number of triples loaded

        """
        # Detect if source is URL or file path
        source_str = str(source)

        if source_str.startswith(("http://", "https://")):
            count = self.load_from_url(source_str, format=format, enrich=enrich)
        else:
            count = self.load_from_file(Path(source), format=format, enrich=enrich)

        # TODO: Implement subgraph loading if needed
        if load_subgraphs:
            log.warning("Subgraph loading not yet implemented")

        return count

    def load_multiple_sources(
        self,
        sources: list[tuple[str | Path, str]],
    ) -> dict[str, int]:
        """Load multiple vocabulary sources.

        Args:
            sources: List of (source, format) tuples

        Returns:
            Dictionary mapping source names to number of triples loaded

        """
        results = {}

        for source, format_type in sources:
            source_name = str(source)
            try:
                count = self.load_vocabulary_source(source, format=format_type)
                results[source_name] = count
            except Exception:
                log.exception("Error loading source: %s", source_name)
                results[source_name] = 0

        total = sum(results.values())
        log.info("Loaded total of %d triples from %d sources", total, len(results))

        return results

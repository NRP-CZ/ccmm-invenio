#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""RDF triplestore management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import Graph, Namespace

if TYPE_CHECKING:
    from rdflib.namespace import DefinedNamespace

log = logging.getLogger(__name__)


class RDFTripleStore:
    """RDF triplestore wrapper for vocabulary conversion."""

    def __init__(self) -> None:
        """Initialize an empty RDF triplestore."""
        self.graph = Graph()
        self._bind_default_namespaces()
        log.info("Initialized RDF triplestore")

    def _bind_default_namespaces(self) -> None:
        """Bind commonly used namespaces to the graph."""
        # Standard namespaces
        self.graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
        self.graph.bind("dc", Namespace("http://purl.org/dc/elements/1.1/"))
        self.graph.bind("dcterms", Namespace("http://purl.org/dc/terms/"))
        self.graph.bind("rdf", Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
        self.graph.bind("rdfs", Namespace("http://www.w3.org/2000/01/rdf-schema#"))
        self.graph.bind("owl", Namespace("http://www.w3.org/2002/07/owl#"))

        # CCMM-specific namespaces
        self.graph.bind("ccmm", Namespace("https://vocabs.ccmm.cz/registry/codelist/"))
        self.graph.bind("ccmm_props", Namespace("http://vocabs.ccmm.cz/props/"))

        # SSSOM namespaces
        self.graph.bind("sssom", Namespace("https://w3id.org/sssom/"))
        self.graph.bind("semapv", Namespace("https://w3id.org/semapv/vocab/"))

        log.debug("Bound default namespaces to graph")

    def bind_namespace(self, prefix: str, namespace: str | DefinedNamespace) -> None:
        """Bind a custom namespace to the graph.

        Args:
            prefix: The namespace prefix (e.g., 'foaf')
            namespace: The namespace URI or DefinedNamespace

        """
        if isinstance(namespace, str):
            namespace = Namespace(namespace)
        self.graph.bind(prefix, namespace)
        log.debug("Bound namespace %s to %s", prefix, namespace)

    def merge(self, other_graph: Graph) -> None:
        """Merge another graph into this triplestore.

        Args:
            other_graph: The RDF graph to merge

        """
        before_count = len(self.graph)
        self.graph += other_graph
        after_count = len(self.graph)
        added_count = after_count - before_count
        log.info("Merged graph: added %d triples (total: %d)", added_count, after_count)

    def size(self) -> int:
        """Return the number of triples in the store."""
        return len(self.graph)

    def query(self, sparql_query: str, **kwargs: object) -> object:
        """Execute a SPARQL query on the triplestore.

        Args:
            sparql_query: The SPARQL query string
            **kwargs: Additional arguments passed to graph.query()

        Returns:
            Query results

        """
        return self.graph.query(sparql_query, **kwargs)

    def serialize(self, format: str = "turtle") -> str:  # noqa: A002
        """Serialize the graph to a string.

        Args:
            format: The serialization format (turtle, xml, n3, etc.)

        Returns:
            Serialized graph as string

        """
        return self.graph.serialize(format=format)

    def serialize_sorted(self, format: str = "turtle") -> str:  # noqa: A002
        """Serialize the graph to a sorted string for stable output.

        This uses ttlser library to produce deterministic, Git-friendly Turtle output.

        Args:
            format: The serialization format (only 'turtle' supported)

        Returns:
            Sorted serialized graph as string

        """
        from io import BytesIO

        if format != "turtle":
            msg = f"Sorted serialization only supports turtle format, got: {format}"
            raise ValueError(msg)

        # Use ttlser for sorted Turtle output
        from ttlser import DeterministicTurtleSerializer

        serializer = DeterministicTurtleSerializer(self.graph)
        stream = BytesIO()
        serializer.serialize(stream)
        return stream.getvalue().decode("utf-8")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"RDFTripleStore(triples={len(self.graph)})"

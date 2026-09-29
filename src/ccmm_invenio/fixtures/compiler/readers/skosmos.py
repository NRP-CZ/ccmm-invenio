#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for codelists published by a Skosmos instance."""

from __future__ import annotations

from typing import override
from urllib.parse import quote, urlsplit

from rdflib import RDF, SKOS, Graph

from .base import VocabularyReader


class SkosmosReader(VocabularyReader):
    """A reader for codelists published by a Skosmos instance, via its REST API.

    The codelist URI (e.g. ``https://vocabs.ccmm.cz/registry/codelist/RelationType/``)
    does not support content negotiation - it always redirects to the HTML page.
    The RDF is therefore fetched from the Skosmos REST data endpoint instead:
    ``{base}/rest/v1/{vocabulary}/data?uri={codelist uri}``, which for a flat
    codelist returns the whole of it - the concept scheme and the RDF of all
    its skos:Concepts.

    Hierarchical codelists need more care: the data endpoint serves only the
    concept scheme and its top concepts for the codelist URI, so the nested
    concepts have to be fetched individually as well (see e.g.
    :class:`CCMMRolesReader`).
    """

    @override
    def read(self) -> Graph:
        """Read the codelist RDF from the Skosmos REST data endpoint."""
        return self.fetch_source()

    @override
    def fetch_source(self) -> Graph:
        """Fetch the source graph of the codelist.

        The codelist is fetched as a whole through the REST data endpoint.
        Hierarchical codelists use :meth:`fetch_nested_source` instead: the
        endpoint serves only the concept scheme and the top concepts for the
        codelist URI, the nested concepts appear in the top concepts' data
        without their details (definitions, ...).
        """
        return self.fetch_graph(self.data_url())

    def fetch_nested_source(self) -> Graph:
        """Fetch the whole nested codelist, concept by concept.

        The data endpoint serves only the top concepts for the codelist URI,
        so every discovered concept is fetched individually as well.
        """
        graph = self.fetch_graph(self.data_url())
        fetched: set[str] = set()
        while pending := [
            str(concept) for concept in graph.subjects(RDF.type, SKOS.Concept) if str(concept) not in fetched
        ]:
            fetched.update(pending)
            for uri in pending:
                graph += self.fetch_graph(self.data_url(uri))
        return graph

    def fetch_graph(self, url: str) -> Graph:
        """Fetch and parse the turtle RDF served at the given URL."""
        graph = Graph()
        graph.parse(url, format="turtle")
        return graph

    def data_url(self, uri: str | None = None) -> str:
        """REST data URL serving the RDF of the given (or own) URI."""
        uri = str(self.uri) if uri is None else uri
        parsed = urlsplit(uri)
        base = f"{parsed.scheme}://{parsed.netloc}"
        vocabulary = self.vocabulary_id(uri)
        return f"{base}/rest/v1/{vocabulary}/data?uri={quote(uri, safe='')}&format=text/turtle"

    def vocabulary_id(self, uri: str) -> str:
        """Return the Skosmos vocabulary id serving the given URI."""
        # e.g. .../registry/codelist/RelationType/ -> RelationType
        return urlsplit(uri).path.rstrip("/").rsplit("/", 1)[-1]

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the INSPIRE theme register."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

from rdflib import SKOS, Graph, Literal, URIRef

from ..constants import PROPS_NAMESPACE, SUPPORTED_LABEL_LANGUAGES
from .base import RehomingReader

if TYPE_CHECKING:
    from rdflib.term import Node

INSPIRE_SCHEME = "INSPIRE"
"""The subject scheme the INSPIRE themes classify under; its lowercase form prefixes
the entry ids (``ef`` -> ``inspire:ef``), as :data:`~.subjects.SUBJECT_SCHEME` does for FORD."""

INSPIRE_VALID = URIRef("http://inspire.ec.europa.eu/registry/status/valid")
"""adms:status of the themes in force - the retired and superseded ones are not read."""

ADMS_STATUS = URIRef("http://www.w3.org/ns/adms#status")


class InspireThemesReader(RehomingReader):
    """A reader for the INSPIRE spatial data themes (``http://inspire.ec.europa.eu/theme``).

    The register serves the themes as SKOS concepts in one RDF/XML document per
    language (``theme.<lang>.rdf``), each with the labels and definitions in that
    language only - the documents of the supported label languages are merged.
    The themes are re-homed into the NMA subjects namespace under the scheme-prefixed
    theme codes (``http://inspire.ec.europa.eu/theme/ef`` -> ``inspire:ef``) and carry
    the theme code as their ``classification_code`` prop, upper case the way CCMM
    records use it (``EF``).
    """

    vocabulary_type = "subjects"

    def __init__(self, uri: str = "http://inspire.ec.europa.eu/theme"):
        """Initialize the reader with the URI of the theme register."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the subjects graph of the INSPIRE themes."""
        return self.rehome(self.fetch_source())

    @override
    def fetch_source(self) -> Graph:
        """Fetch the register documents of the supported label languages and merge them."""
        source = Graph()
        # the register writes non-ISO dates (dct:created) that rdflib warns about while parsing
        rdflib_logger = logging.getLogger("rdflib.term")
        level = rdflib_logger.level
        rdflib_logger.setLevel(logging.CRITICAL)
        try:
            for language in sorted(SUPPORTED_LABEL_LANGUAGES):
                source.parse(self.document_url(language), format="xml")
        finally:
            rdflib_logger.setLevel(level)
        return source

    def document_url(self, language: str) -> str:
        """Return the URL of the RDF document of the register in a language."""
        return f"{self.uri}/theme.{language}.rdf"

    @override
    def source_concepts(self, source: Graph) -> list[URIRef]:
        """Return the valid themes of the register, sorted by their URIs."""
        return sorted(
            (
                concept
                for concept in source.subjects(SKOS.inScheme, URIRef(str(self.uri)))
                if isinstance(concept, URIRef) and (concept, ADMS_STATUS, INSPIRE_VALID) in source
            ),
            key=str,
        )

    @override
    def concept_id(self, name: str) -> str:
        """Return the entry id of a theme code, prefixed with the scheme (``ef`` -> ``inspire:ef``)."""
        return f"{INSPIRE_SCHEME.lower()}:{name.lower()}"

    @override
    def copy_properties(
        self,
        graph: Graph,
        source: Graph,
        source_uri: Node,
        concept_uri: URIRef,
        skip: tuple[Node, ...] = (),
    ) -> None:
        """Copy the labels and definitions of a theme - the register metadata (formats, versions, ...) is not kept."""
        for predicate in (SKOS.prefLabel, SKOS.definition):
            for value in source.objects(source_uri, predicate):
                if isinstance(value, Literal) and value.language in SUPPORTED_LABEL_LANGUAGES:
                    graph.add((concept_uri, predicate, value))

    @override
    def enrich_concept(
        self,
        graph: Graph,
        source: Graph,
        source_uri: URIRef,
        concept_uri: URIRef,
        entry_id: str,
    ) -> None:
        """Add the theme code as the classification_code prop."""
        graph.add((concept_uri, PROPS_NAMESPACE.classification_code, Literal(self.source_name(source_uri).upper())))

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Base reader for the vocabulary fixtures bundled with invenio_rdm_records."""

from __future__ import annotations

import csv
import io
from importlib.resources import files
from typing import TYPE_CHECKING, Any, ClassVar, override

import yaml
from rdflib import SKOS, Graph, Literal, Namespace, URIRef

from ..constants import (
    PROPS_NAMESPACE,
    SUPPORTED_LABEL_LANGUAGES,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations
from .base import NO_SOURCE_URI, VocabularyReader

if TYPE_CHECKING:
    from collections.abc import Mapping
    from importlib.resources.abc import Traversable

FIXTURE_PACKAGE = "invenio_rdm_records.fixtures.data.vocabularies"
"""Package the invenio_rdm_records vocabulary fixtures are shipped in."""


class RDMFixtureReader(VocabularyReader):
    """A reader for the vocabulary fixtures of invenio_rdm_records.

    The fixtures bundled with ``invenio_rdm_records`` share their shape: a
    list of entries identified by their ``id``, language-tagged ``title``
    labels, optional ``description`` texts, ``tags`` and ``props``. Each
    entry becomes a ``skos:Concept`` under an NMA vocabulary namespace,
    carrying the fixture id as the internal id notation and the props under
    their fixture names; subclasses place their entries in the scheme
    hierarchy and add their entry-specific mappings in :meth:`add_entry`.
    The ``icon`` fixture field is a UI concern and is not read.

    YAML fixtures are loaded as-is; CSV ones are normalized first (the
    ``field__subkey`` column names of the flat CSV become the nested entry
    fields, comma-separated ``tags`` become a list - the same mapping
    ``invenio_rdm_records`` itself applies to them).
    """

    fixture_name: ClassVar[str]
    """Filename of the fixture to read, e.g. ``"resource_types.yaml"`` or
    ``"licenses.csv"``."""

    vocabulary_type: ClassVar[str]
    """NMA vocabulary type the concepts are emitted under
    (see :func:`make_vocabulary_namespace`)."""

    def __init__(self, uri: str = NO_SOURCE_URI):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the vocabulary graph from the invenio_rdm_records fixture."""
        graph = Graph()
        graph += semantic_declarations()
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)

        fixture = files(FIXTURE_PACKAGE)
        entries = self.load_entries(fixture / self.fixture_name)

        for entry in entries:
            # the fixture id is the vocabulary entry id; placement in the
            # scheme is left to add_entry below
            concept_uri = self.add_concept(graph, vocabulary, entry["id"], top_concept=False)

            # the labels and descriptions are kept in the supported label
            # languages only; the fixtures are English-only today, but the
            # shape allows any language map
            for lang, title in entry.get("title", {}).items():
                if lang not in SUPPORTED_LABEL_LANGUAGES:
                    continue
                graph.add((concept_uri, SKOS.prefLabel, Literal(title, lang=lang)))

            for lang, description in entry.get("description", {}).items():
                if lang not in SUPPORTED_LABEL_LANGUAGES:
                    continue
                graph.add((concept_uri, SKOS.definition, Literal(description, lang=lang)))

            for tag in entry.get("tags", []):
                graph.add((concept_uri, TAGS_URI, Literal(tag)))

            # the props keep their fixture names; the dot in schema.org is
            # harmless in a URI path segment
            for prop_name, value in entry.get("props", {}).items():
                if not value:
                    continue
                graph.add((concept_uri, PROPS_NAMESPACE[prop_name], Literal(str(value))))

            self.add_entry(graph, vocabulary, concept_uri, entry)
        return graph

    def load_entries(self, fixture_path: Traversable) -> list[dict[str, Any]]:
        """Load the fixture entries, normalizing CSV fixtures on the way."""
        if fixture_path.name.endswith(".csv"):
            text = fixture_path.read_text(encoding="utf-8")
            return [self.csv_entry(row) for row in csv.DictReader(io.StringIO(text))]
        entries: list[dict[str, Any]] = yaml.safe_load(fixture_path.read_text())
        return entries

    def csv_entry(self, row: Mapping[str, str]) -> dict[str, Any]:
        """Normalize one CSV row into the fixture entry shape.

        The flat ``field__subkey`` column names become the nested entry
        fields (``title__en`` -> ``title.en``, ``props__url`` ->
        ``props.url``), the comma-separated ``tags`` become a list.
        """
        entry: dict[str, Any] = {}
        for attr, value in row.items():
            if attr == "tags":
                entry["tags"] = [tag.strip() for tag in value.split(",") if tag.strip()]
                continue
            key, _, subkey = attr.partition("__")
            if subkey:
                entry.setdefault(key, {})[subkey] = value
            else:
                entry[key] = value
        return entry

    def add_entry(
        self,
        graph: Graph,
        vocabulary: Namespace,
        concept_uri: URIRef,
        _entry: dict[str, Any],
    ) -> None:
        """Add the entry-specific triples of a concept.

        By default the concept is placed as a top concept of the scheme;
        subclasses override this to build their hierarchy and map their
        extra fixture data (the entry is passed as ``_entry`` here because
        the default does not need it).
        """
        graph.add((concept_uri, SKOS.topConceptOf, URIRef(vocabulary)))
        graph.add((URIRef(vocabulary), SKOS.hasTopConcept, concept_uri))


class RDMDataciteFixtureReader(RDMFixtureReader):
    """A fixture reader whose entries match their DataCite counterparts.

    The fixture ``props`` carry the DataCite name of the entry under the
    ``datacite`` prop - the concept and the DataCite term it maps to are the
    same concept, so the name is linked via ``skos:exactMatch``.
    """

    datacite_namespace: ClassVar[Namespace]
    """Namespace of the DataCite vocabulary the entries are matched to."""

    @override
    def add_entry(
        self,
        graph: Graph,
        vocabulary: Namespace,
        concept_uri: URIRef,
        entry: dict[str, Any],
    ) -> None:
        """Place the concept as a top concept and match it to DataCite."""
        super().add_entry(graph, vocabulary, concept_uri, entry)

        if value := entry.get("props", {}).get("datacite"):
            graph.add((concept_uri, SKOS.exactMatch, self.datacite_namespace[value]))

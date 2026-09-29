#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""A generic reader for vocabularies from SKOS and other sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from rdflib import RDF, SKOS, Graph, Literal, Namespace, Node, URIRef

from ..constants import (
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    REBUILT_PREDICATES,
    SUPPORTED_LABEL_LANGUAGES,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations

if TYPE_CHECKING:
    from pathlib import Path

PROP_OR_TAG_NAMESPACES = (TAGS_URI, PROPS_NAMESPACE)
"""The namespaces of the interoperability props and tags a curated input
(an overlay or a fragment) may attach to a concept - see
:func:`is_prop_or_tag_predicate`."""

LABEL_PREDICATES = frozenset({SKOS.prefLabel, SKOS.altLabel, SKOS.definition})
"""The predicates whose literals are the human texts of a concept: the
labels and the definitions. The language-tagged ones are kept in the
supported label languages only (see :data:`SUPPORTED_LABEL_LANGUAGES`),
which is what :func:`keep_value` enforces when a reader copies the values
of its source concepts."""


def keep_value(predicate: Node, value: Node) -> bool:
    """Check whether a source value survives the reading.

    Language-tagged labels and definitions (see :data:`LABEL_PREDICATES`)
    are kept in the supported label languages only; literals without a
    language (the plain texts, mapped to English on the export) and all
    the other values pass as they are.
    """
    if predicate not in LABEL_PREDICATES or not isinstance(value, Literal):
        return True
    return value.language is None or value.language in SUPPORTED_LABEL_LANGUAGES


def is_prop_or_tag_predicate(predicate: Node) -> bool:
    """Check whether the predicate is a prop or a tag predicate.

    Shared by :class:`~.overlay.OverlayReader` and
    :class:`~.curated.CuratedVocabularyReader`, the two curated-input
    readers that allow interoperability props and tags among their other
    predicates - see :data:`PROP_OR_TAG_NAMESPACES`.
    """
    return any(str(predicate).startswith(str(namespace)) for namespace in PROP_OR_TAG_NAMESPACES)


def is_plain_literal(value: Node) -> bool:
    """Check whether the value is a plain literal (no datatype, no language).

    Prop and tag values speak strings - the overlays and fragments (see
    :func:`is_prop_or_tag_predicate`) reject anything else, as it would not
    survive the fixture export.
    """
    return isinstance(value, Literal) and not value.datatype and not value.language


NO_SOURCE_URI = "does_not_matter"
"""Placeholder :attr:`VocabularyReader.uri` of readers with no address to
speak of - their source is a bundled fixture, a config dict or an
already-parsed graph passed in some other way (see e.g.
:class:`~.rdm_fixture.RDMFixtureReader`)."""


class VocabularyReader(ABC):
    """A generic reader for vocabularies from SKOS and other sources.

    Readers that re-home the concepts of their source into an NMA
    vocabulary namespace build each concept with :meth:`add_concept` and copy
    the remaining source properties over with :meth:`copy_properties`;
    :class:`RehomingReader` wraps that loop into a shared template.
    Readers whose source is a single RDF document set :attr:`source_format`
    and inherit the :meth:`fetch_source` parsing.
    """

    def __init__(self, uri: str | Path):
        """Initialize the reader with the given URI.

        The URI is the address of the source - its URL for the remote
        sources, the path of the curated file for the local ones; readers
        without one use :data:`NO_SOURCE_URI`.
        """
        self.uri = uri

    source_format: ClassVar[str]
    """RDF serialization of the source document at :attr:`uri` (an rdflib
    parse format, e.g. ``"nt"``). Readers whose source is a single document
    set it and inherit :meth:`fetch_source`; readers that fetch or build
    their source another way (e.g. :class:`SkosmosReader`) leave it unset
    and fetch it themselves."""

    @abstractmethod
    def read(self) -> Graph:
        """Read the SKOS data from the URI and return it as an RDFLib Graph."""
        ...

    def fetch_source(self) -> Graph:
        """Fetch the source document at :attr:`uri` and parse it into a graph."""
        source = Graph()
        source.parse(self.uri, format=self.source_format)
        return source

    def add_concept(
        self,
        graph: Graph,
        vocabulary: Namespace,
        concept_id: str,
        source_uri: Node | None = None,
        top_concept: bool = True,
    ) -> URIRef:
        """Add a concept to a graph with its structural triples.

        The concept is typed, placed into the scheme - as its top concept,
        unless ``top_concept`` is false: a hierarchical vocabulary cannot
        know its top concepts at the read time yet, as they depend on what
        the merge into the target vocabulary covers, so its reader leaves
        the placement to its merger - and carries the lowercase ``concept_id``
        as its internal id notation (the concept URI itself may use another
        case, e.g. a language's uppercase ISO 639-3 code); the source URI,
        when given, is linked back via ``skos:exactMatch``.
        """
        concept_uri = vocabulary[concept_id]
        graph.add((concept_uri, RDF.type, SKOS.Concept))
        graph.add((concept_uri, SKOS.inScheme, URIRef(vocabulary)))
        if top_concept:
            graph.add((concept_uri, SKOS.topConceptOf, URIRef(vocabulary)))
            graph.add((URIRef(vocabulary), SKOS.hasTopConcept, concept_uri))
        graph.add((concept_uri, SKOS.notation, Literal(concept_id.lower(), datatype=NOTATION_ID_DATATYPE)))
        if source_uri is not None:
            graph.add((concept_uri, SKOS.exactMatch, source_uri))
        return concept_uri

    def copy_properties(
        self,
        graph: Graph,
        source: Graph,
        source_uri: Node,
        concept_uri: URIRef,
        skip: tuple[Node, ...] = (),
    ) -> None:
        """Copy the properties of a source concept into the graph.

        Predicates in ``skip`` are not carried over - the reader rebuilds or
        drops them when re-homing the concept; the values pass
        :func:`keep_value`.
        """
        for predicate, value in source.predicate_objects(source_uri):
            if predicate in skip or not keep_value(predicate, value):
                continue
            graph.add((concept_uri, predicate, value))


class RehomingReader(VocabularyReader):
    """A reader that re-homes the concepts of a source graph one by one.

    The readers of whole source graphs - a Skosmos codelist, an authority
    table, an ontology - fetch their source and pass it to :meth:`rehome`,
    which re-homes each of its concepts into the NMA vocabulary namespace
    of :attr:`vocabulary_type` (see :meth:`add_concept` and
    :meth:`copy_properties`). The per-source specifics live in the hooks:
    which concepts are taken (:meth:`source_concepts`), how their ids are
    derived (:meth:`source_name` and :meth:`concept_id`), what is rebuilt
    instead of copied (:attr:`rebuilt_predicates`), whether they are placed
    as top concepts (:attr:`top_concept`) and what else they carry
    (:meth:`enrich_concept`).
    """

    vocabulary_type: ClassVar[str]
    """NMA vocabulary type the concepts are emitted under
    (see :func:`make_vocabulary_namespace`)."""

    rebuilt_predicates: ClassVar[tuple[URIRef, ...]] = REBUILT_PREDICATES
    """Predicates the reader rebuilds itself instead of copying them over;
    subclasses extend this to also drop structure that does not survive the
    re-homing (e.g. the hierarchy of a nested codelist)."""

    top_concept: ClassVar[bool] = True
    """Whether the re-homed concepts are placed as top concepts of the
    scheme. A hierarchical vocabulary cannot know its top concepts at the
    read time yet, as they depend on what the merge into the target
    vocabulary covers - its reader sets this to false and leaves the
    placement to its merger."""

    def rehome(self, source: Graph) -> Graph:
        """Build the vocabulary graph by re-homing the source concepts."""
        graph = Graph()
        graph += semantic_declarations()
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)

        for source_uri in self.source_concepts(source):
            entry_id = self.concept_id(self.source_name(source_uri))
            concept_uri = self.add_concept(graph, vocabulary, entry_id, source_uri, top_concept=self.top_concept)
            self.copy_properties(graph, source, source_uri, concept_uri, self.rebuilt_predicates)
            self.enrich_concept(graph, source, source_uri, concept_uri, entry_id)
        return graph

    def source_concepts(self, source: Graph) -> list[URIRef]:
        """Return the skos:Concepts of the source graph, sorted by their URIs."""
        return sorted(
            (concept for concept in source.subjects(RDF.type, SKOS.Concept) if isinstance(concept, URIRef)),
            key=str,
        )

    def source_name(self, source_uri: URIRef) -> str:
        """Return the local name of a source concept: its last path segment.

        The name is what the entry id is derived from (see
        :meth:`concept_id`).
        """
        return str(source_uri).rstrip("/").rsplit("/", 1)[-1]

    def concept_id(self, name: str) -> str:
        """Return the vocabulary entry id of a source concept name.

        The default is the lowercase name, keeping the concept URI
        machine-readable (``<namespace>/<id>``).
        """
        return name.lower()

    def enrich_concept(
        self,
        graph: Graph,
        source: Graph,
        source_uri: URIRef,
        concept_uri: URIRef,
        entry_id: str,
    ) -> None:
        """Add the source-specific triples of a re-homed concept.

        Called after the concept is re-homed and its properties copied
        over; the default adds nothing.
        """

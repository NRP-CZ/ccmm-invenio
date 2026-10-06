#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers for the relation type vocabularies and their merger."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from rdflib import SKOS, Graph, Literal, URIRef

from ..constants import (
    PROPS_NAMESPACE,
    REBUILT_PREDICATES,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations
from ..merger import SameNamespaceMerger
from .base import VocabularyReader
from .ccmm import CCMMCodelistReader

if TYPE_CHECKING:
    from collections.abc import Callable


class DataciteRelationTypeReader(VocabularyReader):
    """Reader for the DataCite relationType vocabulary published by TIB.

    The concepts are read from the graph ``graph_builder`` returns - a
    single already-parsed document containing the scheme and all of its
    concepts (e.g. :func:`~.converter.datacite_distribution`). It is called
    lazily, from :meth:`read`, so that constructing the reader does not
    fetch the distribution.
    """

    def __init__(
        self,
        graph_builder: Callable[[], Graph],
        uri: str = "https://w3id.org/tib/datacite/vocab/relationType",
    ):
        """Initialize the reader with the given source graph builder and URI.

        Args:
            graph_builder: a zero-argument callable returning a graph
                already containing the scheme and its concepts, e.g.
                :func:`~.converter.datacite_distribution`
            uri: the relationType concept scheme URI

        """
        super().__init__(uri)
        self.graph_builder = graph_builder

    @override
    def read(self) -> Graph:
        """Build the relation types vocabulary graph from the DataCite distribution."""
        graph = Graph()
        graph += semantic_declarations()
        relation_types = make_vocabulary_namespace("relationtypes")
        source_graph = self.graph_builder()

        for tib_uri in source_graph.objects(URIRef(str(self.uri)), SKOS.hasTopConcept):
            name = str(tib_uri).rsplit("/", 1)[-1]
            # the concept URI carries the lowercase name, so that
            # <namespace>/<id> returns the machine understandable information
            concept_uri = self.add_concept(graph, relation_types, name.lower(), tib_uri)

            graph.add((concept_uri, PROPS_NAMESPACE.datacite, Literal(name)))

            self.copy_properties(graph, source_graph, tib_uri, concept_uri, REBUILT_PREDICATES)
        return graph


class CCMMRelationTypeReader(CCMMCodelistReader):
    """Reader for the relation types published by techlib's CCMM registry.

    The source (``https://vocabs.ccmm.cz/registry/codelist/RelationType``) is a
    Skosmos codelist whose concepts carry language-tagged prefLabels (cs, en).
    No ``datacite`` prop is set - the CCMM names are close to, but not
    guaranteed to be, DataCite names.
    """

    vocabulary_type = "relationtypes"

    def __init__(self, uri: str = "https://vocabs.ccmm.cz/registry/codelist/RelationType/"):
        """Initialize the reader with the given URI."""
        super().__init__(uri)


class RelationTypesMerger(SameNamespaceMerger):
    """Merge the CCMM relation types into the DataCite relation types.

    Both readers emit their concepts under the same names, so the concepts
    are matched by URI (see :class:`~.merger.SameNamespaceMerger` for what
    such a merge does). The CCMM labels replace the DataCite term names
    (e.g. "is cited by" replaces "IsCitedBy" for English).
    """

    vocabulary_type: ClassVar[str] = "relationtypes"

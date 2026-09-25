#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the resource types fixture of invenio_rdm_records."""

from __future__ import annotations

from typing import Any, ClassVar, override

from rdflib import RDF, SKOS, Graph, Namespace, Node, URIRef

from ..constants import (
    COAR_RESOURCE_TYPE_NAMESPACE,
    DATACITE_RESOURCE_TYPE_NAMESPACE,
    REBUILT_PREDICATES,
)
from ..merger import SameNamespaceMerger
from .base import RehomingReader
from .rdm_fixture import RDMFixtureReader

COAR_RESOURCE_TYPE_EXPIRES = URIRef("http://purl.org/coar/resource_type/schema#expires")
"""The COAR predicate marking a concept as expired: the concept is
deprecated and no longer part of the vocabulary."""


class RDMResourceTypesReader(RDMFixtureReader):
    """A reader for the InvenioRDM resource types vocabulary.

    The resource types are read from the YAML fixture bundled with
    ``invenio_rdm_records`` (``vocabularies/resource_types.yaml``); entries
    without a subtype are the top concepts, the subtype entries hang below
    them via ``skos:broader``/``skos:narrower``.
    """

    fixture_name = "resource_types.yaml"
    vocabulary_type = "resourcetypes"

    @override
    def add_entry(
        self,
        graph: Graph,
        vocabulary: Namespace,
        concept_uri: URIRef,
        entry: dict[str, Any],
    ) -> None:
        """Place the concept in the subtype hierarchy and map its props."""
        props = entry.get("props", {})
        parent_uri = vocabulary[props["type"]]
        if props.get("subtype"):
            graph.add((concept_uri, SKOS.broader, parent_uri))
            graph.add((parent_uri, SKOS.narrower, concept_uri))
        else:
            super().add_entry(graph, vocabulary, concept_uri, entry)

        for prop_name, value in props.items():
            if not value:
                continue
            if prop_name == "datacite_general":
                # the concept is a subtype of the DataCite resource type
                # general class it maps to
                graph.add(
                    (
                        concept_uri,
                        SKOS.broadMatch,
                        DATACITE_RESOURCE_TYPE_NAMESPACE[value],
                    )
                )
            if prop_name == "schema.org":
                # the schema.org classes are broader than the specialized
                # resource types mapped to them
                graph.add((concept_uri, SKOS.broadMatch, URIRef(value)))


class COARResourceTypesReader(RehomingReader):
    """A reader for the resource types vocabulary published by COAR.

    The source (``https://vocabularies.coar-repositories.org/resource_types/``)
    is a hierarchical SKOS vocabulary of a hundred-ish resource types carrying
    multilingual prefLabels and altLabels, English definitions, hierarchy
    links and mapping links to other vocabularies (eprints, fabio, schema.org).
    Concepts COAR marks as expired are deprecated and are not read.

    The concepts are re-homed into the NMA resourcetypes namespace under their
    lowercased COAR codes (e.g. ``C53B-JCY5`` -> ``c53b-jcy5``, see
    :meth:`add_concept`). The hierarchy is carried by the
    ``skos:broader`` links only - the narrower links the source publishes
    symmetrically are dropped - and still points at the COAR concepts, as the
    reader cannot know which of the concepts the target vocabulary covers:
    both the re-targeting of the links and the placement of the concepts in
    the scheme are the business of :class:`ResourceTypesMerger`.
    """

    vocabulary_type: ClassVar[str] = "resourcetypes"

    rebuilt_predicates: ClassVar[tuple[URIRef, ...]] = (*REBUILT_PREDICATES, SKOS.narrower)
    """Predicates the reader rebuilds itself instead of copying them over:
    the structure, and the narrower links the vocabulary does not carry - the
    hierarchy is expressed by the broader links only."""

    top_concept: ClassVar[bool] = False
    """The placement in the scheme is the business of the merger: a concept
    becomes a top concept only when the merge finds no re-targeted parent."""

    source_format: ClassVar[str] = "nt"
    """The N-Triples distribution the vocabulary publishes."""

    def __init__(
        self,
        uri: str = "https://vocabularies.coar-repositories.org/resource_types/resource_types.nt",
    ):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the resource types vocabulary graph from the COAR resource types."""
        return self.rehome(self.fetch_source())

    @override
    def source_concepts(self, source: Graph) -> list[URIRef]:
        """Return the non-expired COAR concepts, sorted by their URIs."""
        return [uri for uri in super().source_concepts(source) if (uri, COAR_RESOURCE_TYPE_EXPIRES, None) not in source]


class ResourceTypesMerger(SameNamespaceMerger):
    """Merge the COAR resource types into the InvenioRDM resource types.

    The source is the vocabulary read by :class:`COARResourceTypesReader`; a
    COAR concept is matched to its counterpart in the target by the
    ``skos:exactMatch`` link to the COAR concept - the link the resource
    types mapping set (``data/resource_types.yaml``) carries on the RDM types
    it maps. A matched concept keeps its curated RDM data as it is: the COAR
    properties are not merged over it. A concept without a counterpart is
    added under its re-homed URI (the lowercased COAR code) with its COAR
    properties; its ``skos:broader`` links are re-targeted from the COAR
    concepts to the concepts of the target vocabulary - the counterpart of a
    parent that has one there, or the re-homed URI of a parent added
    alongside. A link to a COAR concept that was not read (a deprecated one)
    is dropped. The added concepts are placed in the scheme by the merge: a
    top concept when they have no re-targeted parent, no top concept when
    they do.
    """

    vocabulary_type: ClassVar[str] = "resourcetypes"

    @override
    def merge(self, add_missing: bool = False) -> Graph:
        """Add the source concepts the target vocabulary does not cover.

        Unlike the base class, the concepts with a counterpart are not merged
        into: the target covers them with its own curated data, and merging
        the COAR properties over them (e.g. its lowercase English
        prefLabels) would degrade it. The concepts without a counterpart are
        added when ``add_missing`` is set; without it, the merge is a no-op.
        """
        for source_concept_uri in self._source_concepts():
            if self.find_in_target(source_concept_uri) is not None:
                continue
            if add_missing:
                self._merge_concept(source_concept_uri, self._add_missing_concept(source_concept_uri))
        return self.target_graph

    @override
    def find_in_target(self, source_concept_uri: URIRef) -> URIRef | None:
        """Return the target concept linked to the COAR concept of the source.

        Only the ``skos:exactMatch`` link to the COAR concept itself
        counts; the other exactMatches of a COAR concept point at foreign
        vocabularies and match nothing in the target.
        """
        for coar_uri in self.source_graph.objects(source_concept_uri, SKOS.exactMatch):
            if not str(coar_uri).startswith(str(COAR_RESOURCE_TYPE_NAMESPACE)):
                continue
            for target_uri in self.target_graph.subjects(SKOS.exactMatch, coar_uri):
                if isinstance(target_uri, URIRef):
                    return target_uri
        return None

    @override
    def transform_predicate(self, predicate_name: URIRef, value: Node) -> list[tuple[URIRef, Node]]:
        """Re-target the broader links of a concept, pass the rest as it is.

        A ``skos:broader`` link to a COAR concept points at the target
        concept the reference is re-targeted to; a link to a COAR concept
        that was not read is dropped.
        """
        if (
            predicate_name == SKOS.broader
            and isinstance(value, URIRef)
            and str(value).startswith(str(COAR_RESOURCE_TYPE_NAMESPACE))
        ):
            if rehomed := self.rehomed_reference(value):
                return [(predicate_name, rehomed)]
            return []
        return [(predicate_name, value)]

    def rehomed_reference(self, coar_uri: URIRef) -> URIRef | None:
        """Return the target URI a reference to a COAR concept points at.

        The counterpart of the referenced concept when the target has one
        (see :meth:`find_in_target`), its re-homed URI when it is being added
        as well; ``None`` when it was not read (a deprecated concept).
        """
        code = str(coar_uri)[len(str(COAR_RESOURCE_TYPE_NAMESPACE)) :].lower()
        source_uri = self.source_namespace[code]
        if (source_uri, RDF.type, SKOS.Concept) not in self.source_graph:
            return None
        return self.find_in_target(source_uri) or source_uri

    @override
    def _merge_concept(self, source_concept_uri: URIRef, target_concept_uri: URIRef) -> None:
        """Merge one added concept and place it in the scheme."""
        super()._merge_concept(source_concept_uri, target_concept_uri)

        # the reader does not know which of the concepts the target covers,
        # so it cannot place them in the scheme - the merge does: a concept
        # without a re-targeted parent is a top concept of the scheme
        self._update_scheme_structure(target_concept_uri, top_concept=True)

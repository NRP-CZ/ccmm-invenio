#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Merging of vocabulary graphs into each other."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, override

from rdflib import RDF, SKOS, Graph, Literal, Namespace, Node, URIRef

from .constants import PROPS_NAMESPACE, make_vocabulary_namespace


class VocabularyMerger(ABC):
    """Merge the concepts of a source vocabulary graph into a target graph.

    Subclasses define how a source concept is matched to a target concept
    (:meth:`find_in_target`) and how the properties of the source concept are
    rewritten on the way over (:meth:`transform_predicate`). Source concepts
    without a counterpart in the target are skipped, and values the target
    already carries are not duplicated - for string literals, a value that
    differs from an existing one only in its language tag counts as already
    present.

    Predicates are additive by default - a value is added when the target
    does not carry it yet (tags, ``skos:exactMatch``, ...). Scalar predicates
    instead have their merged value replace the one the target carries (per
    language for language-tagged literals, per datatype for typed literals,
    otherwise the single value overall). A predicate is scalar when it is
    listed in :attr:`single_valued_predicates` or lives in one of the
    :attr:`single_valued_namespaces` - e.g. ``skos:prefLabel`` stays single
    per language and a prop is single overall.
    """

    single_valued_predicates: frozenset[URIRef] = frozenset({SKOS.prefLabel, SKOS.notation})
    """Scalar predicates shared by our vocabularies: one label per language,
    one notation per datatype (id, euvoc codes)."""

    single_valued_namespaces: frozenset[Namespace] = frozenset({PROPS_NAMESPACE})
    """Namespaces whose every property is scalar - all our props are single
    valued, and they cannot be enumerated as they grow with the vocabularies."""

    def __init__(
        self,
        source_namespace: Namespace,
        source_graph: Graph,
        target_namespace: Namespace,
        target_graph: Graph,
    ):
        """Initialize the merger with the source and the target to work on.

        Args:
            source_namespace: concepts of this namespace are merged
            source_graph: the graph the source concepts are read from
            target_namespace: the namespace of the target vocabulary
            target_graph: the graph the concepts are merged into

        """
        self.source_namespace = source_namespace
        self.target_namespace = target_namespace
        self.source_graph = source_graph
        self.target_graph = target_graph

    def merge(self, add_missing: bool = False) -> Graph:
        """Merge the source concepts into the target graph and return it.

        For each concept of the source namespace, its counterpart in the
        target vocabulary is looked up with :meth:`find_in_target`. Each
        property of a found concept is rewritten with
        :meth:`transform_predicate` and then merged by two rules:

        * scalar predicates (:meth:`_is_single_valued`) always replace the
          value the target carries (:meth:`_replace_in_target`)
        * array predicates are additive - a value is added only when the
          target does not carry it yet (:meth:`_exists_in_target`)

        Args:
            add_missing: also merge concepts without a counterpart in the
                target, creating them in the target namespace (instead of
                skipping them)

        """
        for source_concept_uri in self._source_concepts():
            target_concept_uri = self.find_in_target(source_concept_uri)

            if target_concept_uri is None:
                if not add_missing:
                    continue
                target_concept_uri = self._add_missing_concept(source_concept_uri)

            self._merge_concept(source_concept_uri, target_concept_uri)

        return self.target_graph

    def _merge_concept(self, source_concept_uri: URIRef, target_concept_uri: URIRef) -> None:
        """Merge one source concept into the target graph."""
        for predicate, value in self._get_transformed_predicates(source_concept_uri):
            if self._is_single_valued(predicate):
                self._replace_in_target(target_concept_uri, predicate, value)
            elif not self._exists_in_target(target_concept_uri, predicate, value):
                self.target_graph.add((target_concept_uri, predicate, value))

    def _update_scheme_structure(self, concept_uri: URIRef, *, top_concept: bool) -> None:
        """Update the top concept structure of the target scheme around a concept.

        A concept that hangs below another one is no top concept of the
        scheme: its ``skos:topConceptOf`` link and its inverse are
        removed. A concept without a parent becomes a top concept when
        ``top_concept`` is set, in both directions - a merged concept
        carries the link to the scheme at most in the direction its source
        provides, as the scheme itself is not a source concept.
        """
        scheme = URIRef(str(self.target_namespace))
        if (concept_uri, SKOS.broader, None) in self.target_graph:
            self.target_graph.remove((concept_uri, SKOS.topConceptOf, scheme))
            self.target_graph.remove((scheme, SKOS.hasTopConcept, concept_uri))
        elif top_concept:
            self.target_graph.add((concept_uri, SKOS.topConceptOf, scheme))
            self.target_graph.add((scheme, SKOS.hasTopConcept, concept_uri))

    def _add_missing_concept(self, source_concept_uri: URIRef) -> URIRef:
        """Create the target concept for a source concept without one.

        The concept is placed into the target namespace under the same local
        name as in the source namespace and its (transformed) properties are
        then merged as usual.
        """
        local_name = str(source_concept_uri)[len(str(self.source_namespace)) :]
        return self.target_namespace[local_name]

    def _source_concepts(self) -> list[URIRef]:
        """Return all concept URIs of the source namespace, sorted."""
        return sorted(
            subject
            for subject in set(self.source_graph.subjects())
            if isinstance(subject, URIRef) and str(subject).startswith(str(self.source_namespace))
        )

    def _is_single_valued(self, predicate: URIRef) -> bool:
        """Check whether the predicate is scalar and must not accumulate values.

        True for the predicates of :attr:`single_valued_predicates` and for
        every predicate of :attr:`single_valued_namespaces`; false for the
        additive ones (tags, ``skos:exactMatch``, ...).
        """
        if predicate in self.single_valued_predicates:
            return True
        return any(str(predicate).startswith(str(namespace)) for namespace in self.single_valued_namespaces)

    def _replace_in_target(self, target_concept_uri: URIRef, predicate: URIRef, value: Node) -> None:
        """Merge a value of a single-valued predicate, replacing what is there.

        Language-tagged literals replace only the values of the same language
        (so e.g. ``skos:prefLabel`` keeps one value per language), typed
        literals only the values of the same datatype (so the id notation does
        not disturb foreign notations), everything else replaces all values of
        the predicate. The value is then added - when the source carries
        several values for such a predicate, the last one wins.
        """
        if isinstance(value, Literal) and (value.language is not None or value.datatype is not None):
            for existing in list(self.target_graph.objects(target_concept_uri, predicate)):
                if (
                    isinstance(existing, Literal)
                    and existing.language == value.language
                    and existing.datatype == value.datatype
                ):
                    self.target_graph.remove((target_concept_uri, predicate, existing))
        else:
            self.target_graph.remove((target_concept_uri, predicate, None))
        self.target_graph.add((target_concept_uri, predicate, value))

    def _exists_in_target(self, target_concept_uri: URIRef, predicate: URIRef, value: Node) -> bool:
        """Check whether the target concept already carries the given value.

        A value exists when the target contains the exact ``(concept,
        predicate, value)`` triple. For string literals the check extends to
        language variants: a literal also exists when the target carries the
        same string under the same predicate with a different language tag (or
        with none), so a string is never merged twice only because its
        language differs.
        """
        if (target_concept_uri, predicate, value) in self.target_graph:
            return True
        if isinstance(value, Literal) and value.datatype is None:
            return any(
                isinstance(existing, Literal) and existing.datatype is None and str(existing) == str(value)
                for existing in self.target_graph.objects(target_concept_uri, predicate)
            )
        return False

    def _get_transformed_predicates(self, source_concept_uri: URIRef) -> list[tuple[URIRef, Node]]:
        """Return all transformed (predicate, value) pairs of a source concept.

        Every property of the source concept is passed through
        :meth:`transform_predicate` and the results are flattened into a
        single list.
        """
        transformed: list[tuple[URIRef, Node]] = []
        for predicate, value in self.source_graph.predicate_objects(source_concept_uri):
            # a predicate that is not a URIRef (a blank node) cannot be
            # re-homed and has no meaningful transformed form
            if isinstance(predicate, URIRef):
                transformed.extend(self.transform_predicate(predicate, value))
        return transformed

    @abstractmethod
    def find_in_target(self, source_concept_uri: URIRef) -> URIRef | None:
        """Return the target concept URI for the given source concept URI.

        Return ``None`` when the source concept has no counterpart in the
        target vocabulary - such concepts are skipped during the merge.
        """
        ...

    @abstractmethod
    def transform_predicate(self, predicate_name: URIRef, value: Node) -> list[tuple[URIRef, Node]]:
        """Return the (predicate, value) pairs for one source property.

        Called for every property of a source concept. Return an empty list
        to drop the property from the merge.
        """
        ...


class SameNamespaceMerger(VocabularyMerger):
    """Merge source concepts into a target sharing the same namespace.

    Both vocabularies emit their concepts under the NMA vocabulary
    namespace of :attr:`vocabulary_type`, so a source concept is matched to
    the target concept of the same URI - a source concept has a counterpart
    exactly when its URI is a concept of the target graph. The properties
    are passed on unchanged; the merge rules take care of the rest: the
    structural triples (type, inScheme, notation, ...) are already set
    identically by both readers and are deduplicated automatically, labels
    and props replace their scalar counterparts, and everything else is
    additive.
    """

    vocabulary_type: ClassVar[str]
    """NMA vocabulary type of the vocabulary both graphs emit into
    (see :func:`~.constants.make_vocabulary_namespace`)."""

    def __init__(self, source_graph: Graph, target_graph: Graph):
        """Initialize the merger with the source and the target to work on.

        Args:
            source_graph: the graph the source concepts are read from
            target_graph: the graph the concepts are merged into

        """
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)
        super().__init__(vocabulary, source_graph, vocabulary, target_graph)

    def find_in_target(self, source_concept_uri: URIRef) -> URIRef | None:
        """Return the concept itself when it exists in the target vocabulary."""
        if (source_concept_uri, RDF.type, SKOS.Concept) in self.target_graph:
            return source_concept_uri
        return None

    def transform_predicate(self, predicate_name: URIRef, value: Node) -> list[tuple[URIRef, Node]]:
        """Pass on every property of the source concepts unchanged."""
        return [(predicate_name, value)]


class CuratedVocabularyMerger(SameNamespaceMerger):
    """Merge a curated fragment of a vocabulary into the vocabulary itself.

    The fragment is the one read by
    :class:`~.readers.curated.CuratedVocabularyReader`: its typed concepts
    (the ones the fragment introduces, e.g. the Creative Commons family
    tree nodes of the licenses) are created in the target when missing,
    its untyped subjects enrich the concepts of the target (their labels,
    definitions, hierarchy) - and such a subject the target does not know
    fails the merge instead of being silently created.

    The top-concept structure follows the hierarchy: a concept the fragment
    places below another one stops being a top concept of the scheme (the
    parent becomes one instead when the fragment introduces it), so that
    the merged graph stays a proper SKOS tree and not a flat list that
    grew branches.
    """

    @override
    def find_in_target(self, source_concept_uri: URIRef) -> URIRef | None:
        """Return the concept itself - or introduce it.

        A typed source concept (see the reader) is introduced by the
        fragment: returning its URI lets :meth:`_merge_concept` create it
        with all its properties. An untyped subject must already be a
        concept of the target - one that is not means the fragment has
        gone stale (a concept was renamed or removed) and fails the merge.
        """
        if (source_concept_uri, RDF.type, SKOS.Concept) in self.target_graph:
            return source_concept_uri
        if (source_concept_uri, RDF.type, SKOS.Concept) in self.source_graph:
            return source_concept_uri
        raise KeyError(f"{source_concept_uri} is not a concept of the target vocabulary, the curated fragment is stale")

    @override
    def _merge_concept(self, source_concept_uri: URIRef, target_concept_uri: URIRef) -> None:
        super()._merge_concept(source_concept_uri, target_concept_uri)

        # the top-concept structure follows the hierarchy: a concept the
        # fragment places below another one stops being a top concept of
        # the scheme, an introduced one without a parent becomes one
        introduced = (source_concept_uri, RDF.type, SKOS.Concept) in self.source_graph
        self._update_scheme_structure(target_concept_uri, top_concept=introduced)


class MappingsMerger:
    """Merge a graph of overlay triples into a vocabulary graph.

    The overlay graph is e.g. the one read by
    :class:`~.readers.sssom.SSSOMMappingsReader` (mapping links that link
    the concepts of a vocabulary to the concepts of other vocabularies via
    the SKOS mapping properties) or by
    :class:`~.readers.overlay.OverlayReader` (curated interoperability
    props and tags of the concepts). Every triple is added to the vocabulary
    graph as it is - but only when its subject is a concept of the
    vocabulary. A subject that is not one means the overlay has gone stale
    (a concept was renamed or removed) and fails the merge instead of being
    silently dropped.
    """

    def __init__(self, mapping_graph: Graph, vocabulary_graph: Graph):
        """Initialize the merger with the mappings and the vocabulary.

        Args:
            mapping_graph: the graph of overlay triples to merge in
            vocabulary_graph: the vocabulary graph the triples are merged
                into (and returned)

        """
        self.mapping_graph = mapping_graph
        self.vocabulary_graph = vocabulary_graph

    def merge(self) -> Graph:
        """Merge the mapping links into the vocabulary graph and return it."""
        for subject, predicate, triple_object in sorted(self.mapping_graph):
            if (subject, RDF.type, SKOS.Concept) not in self.vocabulary_graph:
                raise KeyError(f"{subject} is not a concept of the target vocabulary, the mapping set is stale")
            self.vocabulary_graph.add((subject, predicate, triple_object))
        return self.vocabulary_graph

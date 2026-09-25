#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Reader for curated turtle fragments of vocabulary concepts."""

from __future__ import annotations

from pathlib import Path
from typing import override

from rdflib import RDF, SKOS, Graph, Literal, Namespace, Node, URIRef

from ..constants import (
    NOTATION_ID_DATATYPE,
    make_vocabulary_namespace,
)
from .base import VocabularyReader, is_plain_literal, is_prop_or_tag_predicate

FRAGMENT_PREDICATES = (
    RDF.type,
    SKOS.inScheme,
    SKOS.topConceptOf,
    SKOS.notation,
    SKOS.prefLabel,
    SKOS.definition,
    SKOS.broader,
    SKOS.exactMatch,
)
"""The SKOS predicates a fragment may carry: the concept type, the scheme
membership and the hierarchy (introduced concepts) together with the labels
and definitions (their curated texts) and the authority links of the concepts.
The props and the tags (see :data:`~.base.PROP_OR_TAG_NAMESPACES`) are
allowed as well. Anything else is rejected rather than guessed at - a stray
predicate would either fail the merge downstream or quietly dangle in the
graph."""


class CuratedVocabularyReader(VocabularyReader):
    """A reader for curated turtle fragments of vocabulary concepts.

    The source is a turtle file of our ``data/`` directory: the pieces of a
    vocabulary its external source does not provide itself, e.g. the Czech
    labels, descriptions and hierarchy of the Creative Commons family of
    the licenses. Its subjects come in two kinds - the concepts the fragment
    introduces (typed as ``skos:Concept``) and the untyped ones enriching
    the concepts of the vocabulary - see
    :class:`~.merger.CuratedVocabularyMerger` for what the merge does with
    each kind.

    The file is read as it is, with the shapes checked: every subject must
    be a term of the vocabulary's NMA namespace (the scheme itself is the
    business of the vocabulary, not of the fragment), every predicate must
    be one the fragments may use (:data:`FRAGMENT_PREDICATES`), every
    label and definition must be a language-tagged literal (the curated
    texts speak their language), every notation must be typed with its
    scheme, every hierarchy link must stay within the vocabulary, and an
    introduced concept must carry its id notation and scheme membership.
    """

    def __init__(self, uri: str | Path, vocabulary_type: str):
        """Initialize the reader with the fragment path and vocabulary type.

        Args:
            uri: the path of the fragment turtle file
            vocabulary_type: the NMA vocabulary type of the fragment
                (see :func:`~..constants.make_vocabulary_namespace`)

        """
        super().__init__(uri)
        self.vocabulary_type = vocabulary_type

    @override
    def read(self) -> Graph:
        """Read the fragment into a graph of its concepts and props."""
        graph = Graph()
        graph.parse(Path(self.uri), format="turtle")
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)

        for subject, predicate, value in graph:
            self.check_subject(subject, vocabulary)
            self.check_predicate(predicate)
            self.check_value(subject, predicate, value, vocabulary)

        for subject in set(graph.subjects()):
            if (subject, RDF.type, SKOS.Concept) in graph:
                self.check_introduced_concept(subject, graph, vocabulary)
        return graph

    def check_subject(self, subject: Node, vocabulary: Namespace) -> None:
        """Check that the subject is a term of the vocabulary namespace."""
        if (
            not isinstance(subject, URIRef)
            or not str(subject).startswith(str(vocabulary))
            or str(subject) == str(vocabulary)
        ):
            raise ValueError(f"{self.uri}: {subject} is not a term of the vocabulary namespace ({str(vocabulary)!r})")

    def check_predicate(self, predicate: Node) -> None:
        """Check whether the predicate is one the fragments may use."""
        if predicate not in FRAGMENT_PREDICATES and not is_prop_or_tag_predicate(predicate):
            raise ValueError(
                f"{self.uri}: {predicate} is not a predicate of the "
                f"fragment shapes ({[str(p) for p in FRAGMENT_PREDICATES]})"
            )

    def check_value(self, subject: Node, predicate: Node, value: Node, vocabulary: Namespace) -> None:
        """Check that the value fits the predicate it is bound to."""
        if predicate == RDF.type and value != SKOS.Concept:
            raise ValueError(f"{self.uri}: {value} is not a concept type")

        if predicate in (SKOS.prefLabel, SKOS.definition) and (not isinstance(value, Literal) or not value.language):
            raise ValueError(f"{self.uri}: {value!r} of {subject} is not a language-tagged literal")

        if predicate == SKOS.notation and (not isinstance(value, Literal) or not value.datatype):
            raise ValueError(f"{self.uri}: {value!r} of {subject} is not a typed notation literal")

        if predicate == SKOS.exactMatch and not isinstance(value, URIRef):
            raise ValueError(f"{self.uri}: {value!r} of {subject} is not an authority URI")

        if predicate in (SKOS.inScheme, SKOS.topConceptOf, SKOS.broader) and (
            not isinstance(value, URIRef) or not str(value).startswith(str(vocabulary))
        ):
            raise ValueError(f"{self.uri}: {value!r} of {subject} is not a term of the vocabulary namespace")

        if predicate in (SKOS.inScheme, SKOS.topConceptOf) and str(value) != str(vocabulary):
            raise ValueError(f"{self.uri}: {value!r} of {subject} is not the scheme of the vocabulary")

        if is_prop_or_tag_predicate(predicate) and not is_plain_literal(value):
            raise ValueError(f"{self.uri}: {value!r} of {subject} is not a plain literal")

    def check_introduced_concept(self, subject: Node, graph: Graph, vocabulary: Namespace) -> None:
        """Check that an introduced concept carries its id and its scheme.

        The id notation and the scheme membership are what makes the
        concept survive the merge into the vocabulary and its fixture
        export - a typed subject without them is a mistake of the curation
        rather than a concept the fragment introduces.
        """
        local_name = str(subject)[len(str(vocabulary)) :]
        if (subject, SKOS.notation, Literal(local_name, datatype=NOTATION_ID_DATATYPE)) not in graph:
            raise ValueError(f"{self.uri}: {subject} is typed as a concept but carries no id notation")
        if (subject, SKOS.inScheme, None) not in graph:
            raise ValueError(f"{self.uri}: {subject} is typed as a concept but carries no scheme membership")

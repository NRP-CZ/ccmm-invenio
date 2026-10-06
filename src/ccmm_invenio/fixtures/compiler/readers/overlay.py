#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Reader for turtle overlays of vocabulary props."""

from __future__ import annotations

from pathlib import Path
from typing import override

from rdflib import Graph

from .base import PROP_OR_TAG_NAMESPACES, VocabularyReader, is_plain_literal, is_prop_or_tag_predicate

OVERLAY_PREDICATES = PROP_OR_TAG_NAMESPACES
"""The namespaces the predicates of an overlay must live in.

The overlays carry what the Invenio fixture entries can express: the props
and the tags (see :data:`~.base.PROP_OR_TAG_NAMESPACES`). Anything else is
rejected rather than guessed at - a stray predicate would either fail the
merge downstream or quietly dangle in the graph."""


class OverlayReader(VocabularyReader):
    """A reader for curated turtle overlays of vocabulary props.

    The source is a turtle file of our ``data/`` directory - the shape
    curated there: the concepts of a vocabulary (by their NMA URIs) carrying
    interoperability props (e.g. the openaire and zenodo types of a relation
    type) or tags, that the external sources of the vocabulary do not
    provide themselves.

    The file is read as it is, with two checks: every predicate must be one
    the overlays may use (:data:`OVERLAY_PREDICATES`), and every value must
    be a plain literal - the overlays speak strings, anything else (an IRI,
    a typed or language-tagged literal) would not survive the fixture
    export. The subjects are not checked here; that is the business of the
    vocabulary the overlay enriches (see :class:`MappingsMerger`, which
    fails on a subject the vocabulary does not know).

    The result is an overlay, not a vocabulary: its subjects are not typed
    as concepts.
    """

    def __init__(self, uri: str | Path):
        """Initialize the reader with the path of the overlay turtle file."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Read the overlay into a graph of props triples."""
        graph = Graph()
        graph.parse(Path(self.uri), format="turtle")

        for subject, predicate, value in graph:
            if not is_prop_or_tag_predicate(predicate):
                raise ValueError(
                    f"{self.uri}: {predicate} is not a prop or tag predicate "
                    f"of the overlay namespaces ({[str(p) for p in OVERLAY_PREDICATES]})"
                )
            if not is_plain_literal(value):
                raise ValueError(f"{self.uri}: {value!r} of {subject} is not a plain literal")
        return graph

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Reader for SSSOM mapping sets rendered as YAML."""

from __future__ import annotations

from pathlib import Path
from typing import override

import yaml
from rdflib import Graph, URIRef

from ..constants import SKOS_MAPPING_PROPERTIES
from .base import VocabularyReader

SKOS_MAPPING_PREDICATES: dict[str, URIRef] = {
    identifier: mapping_property
    for name, mapping_property in SKOS_MAPPING_PROPERTIES.items()
    for identifier in (f"skos:{name}", str(mapping_property))
}
"""The predicates a mapping may use, by their CURIE and URI forms.

SSSOM allows other predicates (e.g. ``owl:sameAs``), but our vocabularies
speak SKOS mapping properties - anything else is rejected rather than
guessed at."""


class SSSOMMappingsReader(VocabularyReader):
    """A reader for SSSOM mapping sets rendered as YAML.

    The source is a SSSOM mapping set (see https://mapping-commons.github.io/
    sssom/spec/) in its YAML rendering: the mapping set metadata at the top,
    the ``curie_map`` and one entry per mapping under ``mappings`` - the shape
    curated in our ``data/`` directory. Only the mappings are read, the
    metadata slots carry no RDF representation here.

    Each mapping becomes one triple of the resulting graph: the CURIEs of the
    subject and the object are expanded through the curie map (identifiers
    that are URIs already pass as they are) and the predicate must be one of
    the five SKOS mapping properties (see :data:`SKOS_MAPPING_PREDICATES`).
    Entries without ``predicate_id`` and ``object_id`` describe subjects
    without a counterpart - documentation only, they are skipped.

    The result is a mapping overlay, not a vocabulary: its subjects are not
    typed as concepts, that is the business of the vocabulary the mappings
    enrich (see :class:`~.merger.MappingsMerger`).
    """

    def __init__(self, uri: str | Path):
        """Initialize the reader with the path of the mapping set yaml."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Read the mapping set into a graph of mapping triples."""
        mapping_set = yaml.safe_load(Path(self.uri).read_text(encoding="utf-8"))
        if not isinstance(mapping_set, dict):
            raise TypeError(f"{self.uri}: not a SSSOM mapping set")

        curie_map = mapping_set.get("curie_map") or {}
        graph = Graph()
        for entry in mapping_set.get("mappings") or []:
            if triple := self.mapping_triple(entry, curie_map):
                graph.add(triple)
        return graph

    def mapping_triple(self, entry: dict, curie_map: dict) -> tuple[URIRef, URIRef, URIRef] | None:
        """Return the (subject, predicate, object) of one mapping entry.

        ``None`` for the entries of subjects without a counterpart - they
        carry a comment explaining the absence instead of the mapping.
        """
        if not isinstance(entry, dict):
            raise TypeError(f"{self.uri}: mapping {entry!r} is not a mapping")
        if "predicate_id" not in entry and "object_id" not in entry:
            return None

        for slot in ("subject_id", "predicate_id", "object_id"):
            if slot not in entry:
                raise ValueError(f"{self.uri}: mapping of {entry.get('subject_id', entry)!r} is missing {slot}")

        return (
            self.expand(entry["subject_id"], curie_map),
            self.predicate(entry["predicate_id"], curie_map),
            self.expand(entry["object_id"], curie_map),
        )

    def expand(self, identifier: str, curie_map: dict) -> URIRef:
        """Expand a mapping identifier into its URI.

        A CURIE is expanded through the curie map; an identifier that is a
        URI already is used as it is. Anything else cannot be resolved and
        is an error.
        """
        if "://" in identifier:
            return URIRef(identifier)

        prefix, _, local = identifier.partition(":")
        if prefix in curie_map:
            return URIRef(curie_map[prefix] + local)

        raise ValueError(
            f"{self.uri}: {identifier!r} is neither a URI nor a CURIE of a curie_map prefix ({sorted(curie_map)})"
        )

    def predicate(self, predicate_id: str, curie_map: dict) -> URIRef:
        """Return the SKOS mapping property the predicate_id denotes."""
        identifier = predicate_id
        if "://" not in predicate_id:
            prefix, _, local = predicate_id.partition(":")
            if prefix in curie_map:
                identifier = curie_map[prefix] + local

        predicate = SKOS_MAPPING_PREDICATES.get(identifier)
        if predicate is None:
            raise ValueError(
                f"{self.uri}: {predicate_id!r} is not a SKOS mapping property "
                "of exactMatch, closeMatch, broadMatch, narrowMatch, "
                "relatedMatch"
            )
        return predicate

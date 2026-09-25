#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the subject categories published by techlib's CCMM registry."""

from __future__ import annotations

from typing import ClassVar, override

from rdflib import SKOS, Graph, Literal, URIRef

from ..constants import (
    HIERARCHY_REBUILT_PREDICATES,
    PROPS_NAMESPACE,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations
from .ccmm import CCMMCodelistReader

SUBJECT_SCHEME = "FORD"
"""The scheme name the subject entries classify under (see
:func:`~ccmm_invenio.fixtures.compiler.invenio_export.export_subjects`).

The scheme also prefixes the entry ids: the ids must be unique among all
subject schemes, so the lowercased scheme name stands before the
classification code (``10101`` -> ``ford:10101``) - the way the invenio
subject vocabularies of EuroSciVoc and GEMET build their ids (e.g.
``euroscivoc:1717``), and the way zenodo serves its lowercase subject
schemes (e.g. ``url``)."""


class SubjectsReader(CCMMCodelistReader):
    """A reader for the subject categories published by techlib's CCMM registry.

    The source (``https://vocabs.ccmm.cz/registry/codelist/SubjectCategory``)
    is the OECD FORD (Frascati) classification of research fields - a nested
    Skosmos codelist: its top concepts are the six major fields (``10000``
    Natural sciences, ...) and the finer fields nest below them (``10100``
    Mathematics, ``10100/10101`` Pure mathematics). The REST data endpoint
    serves only the concept scheme and the top concepts for the codelist URI,
    so every discovered concept is fetched individually as well
    (:meth:`fetch_nested_source`).

    The concepts are re-homed into the NMA subjects namespace under the
    scheme-prefixed FORD classification codes (e.g. ``ford:10101``, see
    :data:`SUBJECT_SCHEME` and :meth:`add_concept`). Unlike the flat
    codelists, the hierarchy survives the re-homing: the ``skos:broader``
    links of the source point at the CCMM concepts, so the reader re-targets
    them between the re-homed concepts (with the symmetric
    ``skos:narrower`` links) and places the concepts without a re-homed
    parent at the top of the scheme.
    """

    vocabulary_type = "subjects"

    rebuilt_predicates: ClassVar[tuple[URIRef, ...]] = HIERARCHY_REBUILT_PREDICATES
    """Predicates the reader rebuilds itself instead of copying them over:
    the structure, and the hierarchy links that are re-targeted from the
    CCMM concepts to the re-homed ones."""

    def __init__(self, uri: str = "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/"):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def concept_id(self, name: str) -> str:
        """Return the vocabulary entry id of a CCMM concept name.

        The classification code alone (e.g. ``10101``) is not unique among
        all subject schemes, so the lowercase scheme name is prefixed to it
        (``10101`` -> ``ford:10101``), the way the invenio subject
        vocabularies of EuroSciVoc and GEMET build their ids.
        """
        return f"{SUBJECT_SCHEME.lower()}:{name.lower()}"

    @override
    def fetch_source(self) -> Graph:
        """Fetch the whole nested codelist, concept by concept.

        See :meth:`SkosmosReader.fetch_nested_source`.
        """
        return self.fetch_nested_source()

    @override
    def read(self) -> Graph:
        """Build the subjects vocabulary graph from the CCMM subject categories."""
        graph = Graph()
        graph += semantic_declarations()
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)

        source = self.fetch_source()

        # the concepts are re-homed under their classification codes first;
        # the hierarchy can only be rebuilt once all of them are known
        rehomed: dict[URIRef, URIRef] = {}
        for ccmm_uri in self.source_concepts(source):
            code = self.source_name(ccmm_uri)
            rehomed[ccmm_uri] = self.add_concept(graph, vocabulary, self.concept_id(code), ccmm_uri, top_concept=False)
            self.copy_properties(graph, source, ccmm_uri, rehomed[ccmm_uri], self.rebuilt_predicates)
            # the FORD code, e.g. 10101 (the ccmm subject classification_code)
            graph.add((rehomed[ccmm_uri], PROPS_NAMESPACE.classification_code, Literal(code)))

        for ccmm_uri, concept_uri in rehomed.items():
            parents = [
                broader
                for broader in source.objects(ccmm_uri, SKOS.broader)
                if isinstance(broader, URIRef) and broader in rehomed
            ]
            for parent in parents:
                graph.add((concept_uri, SKOS.broader, rehomed[parent]))
                graph.add((rehomed[parent], SKOS.narrower, concept_uri))
            if not parents:
                graph.add((concept_uri, SKOS.topConceptOf, URIRef(vocabulary)))
                graph.add((URIRef(vocabulary), SKOS.hasTopConcept, concept_uri))
        return graph

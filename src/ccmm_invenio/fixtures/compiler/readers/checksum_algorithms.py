#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the checksum algorithms vocabulary of SPDX.

Note that this reader targets SPDX 2.3. SPDX 3 exists, but CCMM profiles
the 2.3 - the reader must not be pointed at a newer ontology.
"""

from __future__ import annotations

import re
from typing import ClassVar, override

from rdflib import RDF, RDFS, SKOS, Graph, Literal, Namespace, URIRef

from .base import RehomingReader

SPDX_VERSION = "2.3"
"""SPDX version this vocabulary is read from.

SPDX 3 has been released in the meantime, but CCMM profiles SPDX 2.3;
the source URL below pins the ontology of exactly that version.
"""

SPDX_ONTOLOGY_URL = "https://raw.githubusercontent.com/spdx/spdx-spec/support/2.3/ontology/spdx-ontology.owl.xml"
"""OWL ontology of SPDX 2.3, published on the spdx-spec support branch of
that version (the vocabulary document at ``https://spdx.org/rdf/terms``)."""

SPDX_NAMESPACE = Namespace("http://spdx.org/rdf/terms#")
"""RDF terms namespace of SPDX 2.3; the checksum algorithms are its named
individuals (``checksumAlgorithm_<name>``, e.g.
``http://spdx.org/rdf/terms#checksumAlgorithm_blake2b256``) typed as
``spdx:ChecksumAlgorithm``."""

TERM_STATUS = URIRef("http://www.w3.org/2003/06/sw-vocab-status/ns#term_status")
"""Maturity note of an SPDX term - an editorial detail, not carried over."""

COMMENT_ALGORITHM = re.compile(r"Indicates the algorithm used was\s+(.+?)\.?\s*")
"""The SPDX comments naming their algorithm, e.g. "Indicates the algorithm
used was BLAKE2b-256." - the individuals carry no labels of their own, so
the embedded algorithm name is lifted out as the prefLabel."""


class SPDXChecksumAlgorithmsReader(RehomingReader):
    """A reader for the checksum algorithms of the SPDX 2.3 ontology.

    The source is the OWL ontology of SPDX 2.3 (see :data:`SPDX_ONTOLOGY_URL`).
    The checksum algorithms are the named individuals of the
    ``spdx:ChecksumAlgorithm`` class; they carry no labels, only English
    ``rdfs:comment`` texts of the form "Indicates the algorithm used was
    <NAME>." and a ``term_status`` note.

    The individuals are re-homed into the NMA checksumalgorithms namespace
    under their SPDX names without the ``checksumAlgorithm_`` prefix (e.g.
    ``blake2b256``), linked back to the individuals via
    ``skos:exactMatch``. The algorithm name lifted out of the comment
    becomes the prefLabel, the comment itself the definition; the
    ``term_status`` note is an editorial detail and is dropped.
    """

    vocabulary_type: ClassVar[str] = "checksumalgorithms"

    rebuilt_predicates: ClassVar[tuple[URIRef, ...]] = (RDF.type, TERM_STATUS, RDFS.comment)
    """The individuals carry no scheme structure to rebuild: the type goes
    into the concept, the maturity note is dropped and the comment is lifted
    into the label and the definition instead (:meth:`enrich_concept`)."""

    source_format: ClassVar[str] = "xml"
    """The RDF/XML of the SPDX ontology (see :data:`SPDX_ONTOLOGY_URL`)."""

    def __init__(self, uri: str = SPDX_ONTOLOGY_URL):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the checksum algorithms vocabulary graph from the SPDX ontology."""
        return self.rehome(self.fetch_source())

    @override
    def source_concepts(self, source: Graph) -> list[URIRef]:
        """Return the checksum algorithm individuals of the ontology, sorted."""
        individuals = source.subjects(RDF.type, SPDX_NAMESPACE.ChecksumAlgorithm)
        return sorted((individual for individual in individuals if isinstance(individual, URIRef)), key=str)

    @override
    def source_name(self, source_uri: URIRef) -> str:
        """Return the local name of a source individual: its URI fragment."""
        return str(source_uri).rsplit("#", 1)[-1]

    @override
    def concept_id(self, name: str) -> str:
        """Return the vocabulary entry id of an SPDX algorithm name."""
        return name.removeprefix("checksumAlgorithm_").lower()

    @override
    def enrich_concept(
        self,
        graph: Graph,
        source: Graph,
        source_uri: URIRef,
        concept_uri: URIRef,
        entry_id: str,
    ) -> None:
        """Lift the label and the definition of an algorithm out of its comment."""
        comment = source.value(source_uri, RDFS.comment)
        if isinstance(comment, Literal):
            graph.add((concept_uri, SKOS.definition, comment))
            label = entry_id
            if match := COMMENT_ALGORITHM.fullmatch(str(comment)):
                label = match.group(1)
            graph.add((concept_uri, SKOS.prefLabel, Literal(label, lang=comment.language or "en")))

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the file formats vocabulary of the EU Publications Office."""

from __future__ import annotations

from typing import ClassVar, override

from rdflib import RDF, SKOS, Graph, URIRef

from .base import RehomingReader

EU_FILE_TYPES_URL = (
    "http://publications.europa.eu/resource/distribution/file-type/20260715-0/rdf/skos_core/filetypes-skos.rdf"
)
"""Cellar distribution of the EU Publications Office file type table.

This is the persistent URI behind the euvoc download handler
(``https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=...``)
and serves the full RDF/XML of the vocabulary directly - unlike the
vocabulary URI (``http://publications.europa.eu/resource/authority/file-type``),
which serves only concept stubs without labels. The URI pins the
20260715-0 release of the table; bump it to move to a newer release.
"""

OP_MAPPED_CODE = URIRef("http://publications.europa.eu/ontology/authority/op-mapped-code")
"""Links a concept to its mapped codes; the values are blank nodes whose
own triples are not carried along, so the links are dropped."""


class EUFileFormatsReader(RehomingReader):
    """A reader for the file type table of the EU Publications Office.

    The source is the EU Publications Office file type authority table
    (``http://publications.europa.eu/resource/authority/file-type``, served
    as its skos_core cellar distribution - see :data:`EU_FILE_TYPES_URL`).
    Its concepts are flat, each standing for a file format: they carry
    multilingual prefLabels, English altLabels and definitions, the
    deprecated flag, and typed notations - the IANA media type
    (``euvoc:IANA_MT``), the file extension (``euvoc:FILE_EXT``)
    and the cellar media types.

    The concepts are re-homed into the NMA fileformats namespace under
    their lowercased authority codes (e.g. ``PDF`` -> ``pdf``, see
    :meth:`add_concept`), their typed notations coexisting with our id
    notation the same way the euvoc codes do in the languages vocabulary.
    The ``op-mapped-code`` links to mapped codes are dropped - their blank
    node structures would not survive the re-homing.
    """

    vocabulary_type: ClassVar[str] = "fileformats"

    rebuilt_predicates: ClassVar[tuple[URIRef, ...]] = (
        RDF.type,
        SKOS.inScheme,
        SKOS.topConceptOf,
        OP_MAPPED_CODE,
    )
    """Predicates rebuilt or dropped during the re-homing; everything else
    is copied from the authority concepts."""

    source_format: ClassVar[str] = "xml"
    """The RDF/XML served by the cellar distribution (see
    :data:`EU_FILE_TYPES_URL`)."""

    def __init__(self, uri: str = EU_FILE_TYPES_URL):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the file formats vocabulary graph from the EU file type table."""
        return self.rehome(self.fetch_source())

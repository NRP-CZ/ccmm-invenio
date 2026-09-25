#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the DataCite linked-data distribution published by TIB."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from .base import VocabularyReader

if TYPE_CHECKING:
    from rdflib import Graph

DATACITE_DISTRIBUTION_URI = "https://w3id.org/tib/datacite/dist/datacite-4.7.rdf"
"""TIB's integrated distribution of the DataCite classes, properties and
vocabulary schemes for schema version 4.7, as a single RDF file."""


class DataciteReader(VocabularyReader):
    """A reader for the DataCite linked-data distribution published by TIB.

    The distribution is a single RDF file integrating all DataCite classes,
    properties and vocabulary schemes. Parse it once and pass its graph to
    the vocabulary-specific readers (e.g. :class:`DataciteRelationTypeReader`)
    through their ``graph_builder``, so they do not have to fetch each
    vocabulary term as its own document.
    """

    source_format: ClassVar[str] = "xml"
    """The RDF/XML of the distribution (see
    :data:`DATACITE_DISTRIBUTION_URI`)."""

    def __init__(self, uri: str = DATACITE_DISTRIBUTION_URI):
        """Initialize the reader with the given distribution URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Parse the distribution RDF into a graph."""
        return self.fetch_source()

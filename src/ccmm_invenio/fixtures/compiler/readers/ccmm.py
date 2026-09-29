#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers for the codelists published by techlib's CCMM registry."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override
from urllib.parse import urlsplit

from .base import RehomingReader
from .skosmos import SkosmosReader

if TYPE_CHECKING:
    from rdflib import Graph


def kebab_case(name: str) -> str:
    """Return the kebab-case form of a CamelCase concept name."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


class CCMMCodelistReader(SkosmosReader, RehomingReader):
    """A reader for the codelists published by techlib's CCMM registry.

    The source (e.g. ``https://vocabs.ccmm.cz/registry/codelist/RelationType``)
    is a Skosmos codelist; the RDF is fetched through the Skosmos REST data
    endpoint (see :class:`SkosmosReader`). The concepts are re-homed into an
    NMA vocabulary namespace under :meth:`concept_id`-derived ids (see
    :meth:`add_concept` and :meth:`copy_properties`).
    """

    @override
    def read(self) -> Graph:
        """Build the vocabulary graph from the CCMM codelist."""
        return self.rehome(self.fetch_source())

    @override
    def vocabulary_id(self, uri: str) -> str:
        """Return the Skosmos vocabulary id serving the given URI.

        The CCMM registry nests concept URIs below the codelist URI (e.g.
        ``.../codelist/AgentRole/Contributor/DataManager``), so the id is
        the path segment following ``codelist`` rather than the last one -
        the same segment for the codelist URI itself (e.g. ``AgentRole``).
        """
        segments = urlsplit(uri).path.split("/")
        return segments[segments.index("codelist") + 1]

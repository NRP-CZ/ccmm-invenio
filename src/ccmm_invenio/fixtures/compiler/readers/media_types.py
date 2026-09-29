#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Reader for the media types registry of IANA."""

from __future__ import annotations

import csv
import io
import re
from typing import ClassVar, override
from urllib.request import urlopen

from rdflib import SKOS, Graph, Literal

from ..constants import (
    IANA_MEDIA_TYPE_NAMESPACE,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations
from .base import VocabularyReader

IANA_MEDIA_TYPES_URL = "https://www.iana.org/assignments/media-types/"
"""Base URL of the IANA media types registry.

The registry itself (``https://www.iana.org/assignments/media-types/
media-types.xhtml``) has no RDF form - but each of its top-level type
registries is published as a CSV (``{base}/{type}.csv``), whose rows carry
the subtype name, the full media type (the ``Template`` column, e.g.
``application/pdf``) and the reference of its registration (e.g.
``[RFC6015]``).
"""

MEDIA_TYPE_REGISTRIES = (
    "application",
    "audio",
    "font",
    "image",
    "message",
    "model",
    "multipart",
    "text",
    "video",
)
"""Top-level type registries making up the media types registry as a whole."""

DEPRECATED_NAME = re.compile(r"DEPRECATED|OBSOLETE", re.IGNORECASE)
"""Matches the deprecation notes IANA puts into the CSV name column,
e.g. ``rpki-ghostbusters (DEPRECATED)`` or ``javascript (OBSOLETED in favor
of text/javascript)`` - the media type itself stays in the registry."""


class IANAMediaTypesReader(VocabularyReader):
    """A reader for the media types registry of IANA.

    The source is the IANA media types registry (see
    :data:`IANA_MEDIA_TYPES_URL`), fetched as the CSVs of its top-level type
    registries (see :data:`MEDIA_TYPE_REGISTRIES`). Its concepts are flat,
    each standing for a registered media type: the rows carry the media type
    itself (the ``Template`` column), its registration reference and, for
    deprecated or obsoleted types, a note in the name column.

    The concepts are re-homed into the NMA mediatypes namespace under their
    media types (``application/pdf`` -> ``<namespace>/application/pdf``,
    mirroring the structure of the IANA IRIs, see :meth:`add_concept`),
    carrying the media type as the prefLabel and the id notation, the
    registration reference in the definition and a ``deprecated`` tag for
    the deprecated/obsoleted types.
    """

    vocabulary_type: ClassVar[str] = "mediatypes"

    def __init__(self, uri: str = IANA_MEDIA_TYPES_URL):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the media types vocabulary graph from the IANA registry."""
        graph = Graph()
        graph += semantic_declarations()
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)

        for entry in self.fetch_registry_entries():
            media_type = entry["Template"]
            concept_uri = self.add_concept(graph, vocabulary, media_type, IANA_MEDIA_TYPE_NAMESPACE[media_type])

            graph.add((concept_uri, SKOS.prefLabel, Literal(media_type, lang="en")))

            reference = entry["Reference"]
            if reference:
                graph.add(
                    (
                        concept_uri,
                        SKOS.definition,
                        Literal(
                            f"Media type registered by IANA ({reference}).",
                            lang="en",
                        ),
                    )
                )

            if DEPRECATED_NAME.search(entry["Name"]):
                graph.add((concept_uri, TAGS_URI, Literal("deprecated")))

        return graph

    def fetch_registry_entries(self) -> list[dict[str, str]]:
        """Fetch and parse the CSVs of the top-level type registries.

        The rows are sorted by their media type, so that the reader output
        does not depend on the order the registries happen to be listed in.
        """
        entries: list[dict[str, str]] = []
        for registry in MEDIA_TYPE_REGISTRIES:
            # the registry URL is the https IANA base, safe to open
            with urlopen(f"{self.uri}{registry}.csv") as response:  # noqa: S310
                text = response.read().decode("utf-8")
            entries.extend(csv.DictReader(io.StringIO(text)))
        return sorted(entries, key=lambda entry: entry["Template"])

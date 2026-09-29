#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers for the title type vocabularies and their merger."""

from __future__ import annotations

from typing import ClassVar, override

from ..constants import (
    DATACITE_TITLE_TYPE_NAMESPACE,
)
from ..merger import SameNamespaceMerger
from .ccmm import CCMMCodelistReader, kebab_case
from .rdm_fixture import RDMDataciteFixtureReader


class RDMTitleTypesReader(RDMDataciteFixtureReader):
    """A reader for the InvenioRDM title types vocabulary.

    The title types are read from the YAML fixture bundled with
    ``invenio_rdm_records`` (``vocabularies/title_types.yaml``); the
    vocabulary is flat, so all entries are top concepts of the scheme.
    The fixture ``props`` carry the DataCite titleType name of the entry
    under the ``datacite`` prop.
    """

    fixture_name = "title_types.yaml"
    vocabulary_type = "titletypes"
    datacite_namespace = DATACITE_TITLE_TYPE_NAMESPACE


class CCMMTitleTypesReader(CCMMCodelistReader):
    """Reader for the alternate title types published by techlib's CCMM registry.

    The source (``https://vocabs.ccmm.cz/registry/codelist/AlternateTitle``) is
    a Skosmos codelist whose concepts carry language-tagged prefLabels (cs, en).
    The CCMM CamelCase concept names are converted to the kebab-case ids of
    the RDM title types (e.g. ``AlternativeTitle`` -> ``alternative-title``),
    so that the two vocabularies can be merged concept by concept.
    """

    vocabulary_type = "titletypes"

    def __init__(self, uri: str = "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/"):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def concept_id(self, name: str) -> str:
        """Return the kebab-case vocabulary entry id of a CCMM concept name."""
        return kebab_case(name)


class TitleTypesMerger(SameNamespaceMerger):
    """Merge the CCMM title types into the RDM title types.

    The CCMM reader derives the same kebab-case ids as the RDM fixture, so
    the concepts are matched by URI (see :class:`~.merger.SameNamespaceMerger`
    for what such a merge does). The CCMM labels replace the RDM ones
    (e.g. "Alternative Title" replaces "Alternative title" for English).
    """

    vocabulary_type: ClassVar[str] = "titletypes"

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers for the date type vocabularies and their merger."""

from __future__ import annotations

from typing import ClassVar, override

from ..constants import (
    DATACITE_DATE_TYPE_NAMESPACE,
)
from ..merger import SameNamespaceMerger
from .ccmm import CCMMCodelistReader, kebab_case
from .rdm_fixture import RDMDataciteFixtureReader


class RDMDateTypesReader(RDMDataciteFixtureReader):
    """A reader for the InvenioRDM date types vocabulary.

    The date types are read from the YAML fixture bundled with
    ``invenio_rdm_records`` (``vocabularies/date_types.yaml``); the
    vocabulary is flat, so all entries are top concepts of the scheme.
    The fixture ``props`` carry the DataCite dateType name of the entry
    under the ``datacite`` prop.
    """

    fixture_name = "date_types.yaml"
    vocabulary_type = "datetypes"
    datacite_namespace = DATACITE_DATE_TYPE_NAMESPACE


class CCMMDateTypesReader(CCMMCodelistReader):
    """Reader for the time references published by techlib's CCMM registry.

    The source (``https://vocabs.ccmm.cz/registry/codelist/TimeReference``)
    is a Skosmos codelist whose concepts carry language-tagged prefLabels
    (cs, en). The CCMM CamelCase concept names are converted to the
    kebab-case ids of the RDM date types (e.g. ``Copyrighted`` ->
    ``copyrighted``), so that the two vocabularies can be merged concept
    by concept.
    """

    vocabulary_type = "datetypes"

    def __init__(self, uri: str = "https://vocabs.ccmm.cz/registry/codelist/TimeReference/"):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def concept_id(self, name: str) -> str:
        """Return the kebab-case vocabulary entry id of a CCMM concept name."""
        return kebab_case(name)


class DateTypesMerger(SameNamespaceMerger):
    """Merge the CCMM time references into the RDM date types.

    The CCMM reader derives the same kebab-case ids as the RDM fixture, so
    the concepts are matched by URI (see :class:`~.merger.SameNamespaceMerger`
    for what such a merge does). The CCMM labels replace the RDM ones -
    including the English ones, as the CCMM labels are prefixed with the
    shared qualifier (e.g. "Date Accepted" replaces "Accepted").
    """

    vocabulary_type: ClassVar[str] = "datetypes"

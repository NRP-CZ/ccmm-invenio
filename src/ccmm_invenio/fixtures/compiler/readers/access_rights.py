#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the access rights vocabulary published by COAR."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from .base import RehomingReader

if TYPE_CHECKING:
    from rdflib import Graph

ACCESS_STATUS_IDS = {
    "c_abf2": "open",
    "c_f1cf": "embargoed",
    "c_16ec": "restricted",
    "c_14cb": "metadata-only",
}
"""COAR concept code -> vocabulary entry id.

InvenioRDM has no access rights vocabulary - its access statuses are
hardcoded (``invenio_rdm_records.records.systemfields.access.field.record.AccessStatusEnum``).
The ids are therefore aligned with those statuses, so that the vocabulary
can stand in for them; concepts unknown to the mapping keep their COAR
code as the id.
"""


class COARAccessRightsReader(RehomingReader):
    """A reader for the access rights vocabulary published by COAR.

    The source (``https://vocabularies.coar-repositories.org/access_rights/``)
    is a flat SKOS vocabulary of four concepts (open, embargoed, restricted
    and metadata only access) carrying multilingual prefLabels and
    altLabels, English definitions and ``skos:relatedMatch`` links to other
    access rights vocabularies (Eprints, ARCHE).

    The concepts are re-homed into the NMA accessrights namespace under the
    ids of the InvenioRDM access statuses (e.g. ``c_abf2`` -> ``open``, see
    :meth:`add_concept`).
    """

    vocabulary_type: ClassVar[str] = "accessrights"

    source_format: ClassVar[str] = "nt"
    """The N-Triples distribution of the vocabulary: the vocabulary URI
    itself serves HTML only, without content negotiation."""

    def __init__(
        self,
        uri: str = "https://vocabularies.coar-repositories.org/access_rights/access_rights.nt",
    ):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the access rights vocabulary graph from the COAR access rights."""
        return self.rehome(self.fetch_source())

    @override
    def concept_id(self, name: str) -> str:
        """Return the vocabulary entry id of a COAR concept code."""
        return ACCESS_STATUS_IDS.get(name, name.lower())

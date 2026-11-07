# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Reader for the removal reasons fixture of invenio_rdm_records."""

from __future__ import annotations

from .rdm_fixture import RDMFixtureReader


class RDMRemovalReasonsReader(RDMFixtureReader):
    """A reader for the InvenioRDM removal reasons vocabulary.

    The removal reasons are read from the YAML fixture bundled with
    ``invenio_rdm_records`` (``vocabularies/removal_reasons.yaml``); the
    vocabulary is flat, so all entries are top concepts of the scheme and
    the :class:`RDMFixtureReader` defaults apply unchanged.
    """

    fixture_name = "removal_reasons.yaml"
    vocabulary_type = "removalreasons"

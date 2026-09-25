#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers for the role vocabularies and their merger."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from ..constants import (
    DATACITE_CONTRIBUTOR_TYPE_NAMESPACE,
    HIERARCHY_REBUILT_PREDICATES,
)
from ..merger import SameNamespaceMerger
from .ccmm import CCMMCodelistReader
from .rdm_fixture import RDMDataciteFixtureReader

if TYPE_CHECKING:
    from rdflib import Graph, URIRef


class RDMRolesReader(RDMDataciteFixtureReader):
    """A reader for the InvenioRDM roles vocabulary.

    The roles are read from the YAML fixture bundled with
    ``invenio_rdm_records`` (``vocabularies/roles.yaml``); the vocabulary
    is flat, so all entries are top concepts of the scheme. The fixture
    ``props`` carry the DataCite contributorType name of the entry under
    the ``datacite`` prop and its MARC 21 relator code under ``marc``.
    """

    fixture_name = "roles.yaml"
    vocabulary_type = "roles"
    datacite_namespace = DATACITE_CONTRIBUTOR_TYPE_NAMESPACE


class CCMMRolesReader(CCMMCodelistReader):
    """Reader for the agent roles published by techlib's CCMM registry.

    The source (``https://vocabs.ccmm.cz/registry/codelist/AgentRole``) is a
    nested Skosmos codelist: its top concepts are the general agent roles
    (Creator, Contributor, Publisher) and the contributor types nest below
    the Contributor top concept (e.g.
    ``.../AgentRole/Contributor/DataManager``).

    The CCMM CamelCase concept names are lowercased into the ids of the RDM
    roles (e.g. ``DataManager`` -> ``datamanager``), so that the two
    vocabularies can be merged concept by concept. The CCMM hierarchy is
    dropped on the way: the RDM roles are flat, and the grouping under
    Contributor is an artifact of the CCMM registry (every RDM role is a
    DataCite contributor type) rather than a structure worth keeping.
    """

    vocabulary_type = "roles"

    rebuilt_predicates: ClassVar[tuple[URIRef, ...]] = HIERARCHY_REBUILT_PREDICATES

    def __init__(self, uri: str = "https://vocabs.ccmm.cz/registry/codelist/AgentRole/"):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def fetch_source(self) -> Graph:
        """Fetch the whole nested codelist, concept by concept.

        See :meth:`SkosmosReader.fetch_nested_source`.
        """
        return self.fetch_nested_source()


class RolesMerger(SameNamespaceMerger):
    """Merge the CCMM agent roles into the RDM roles.

    The CCMM reader derives the same lowercase ids as the RDM fixture, so
    the concepts are matched by URI (see :class:`~.merger.SameNamespaceMerger`
    for what such a merge does). The CCMM contributions are the Czech labels
    (replacing the RDM ones, e.g. "Projektový manažer" replaces "Manažer
    projektu"), the definitions and the authority links; the general agent
    roles (creator, contributor, publisher) have no RDM counterpart and are
    pulled in with ``merge(add_missing=True)``.
    """

    vocabulary_type: ClassVar[str] = "roles"

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the licenses fixture of invenio_rdm_records."""

from __future__ import annotations

from typing import Any, ClassVar, override

from rdflib import SKOS, Graph, Namespace, URIRef

from ..merger import CuratedVocabularyMerger
from .rdm_fixture import RDMFixtureReader


class RDMLicensesReader(RDMFixtureReader):
    """A reader for the InvenioRDM licenses vocabulary.

    The licenses are read from the CSV fixture bundled with
    ``invenio_rdm_records`` (``vocabularies/licenses.csv``); the vocabulary is
    flat, so all entries are top concepts of the scheme. The fixture
    ``props`` carry the license URL, its identifier scheme (spdx) and the
    OSI approval flag. The concept and the license its URL points to are
    the same concept, so the URL is linked via ``skos:exactMatch``.
    """

    fixture_name = "licenses.csv"
    vocabulary_type = "licenses"

    @override
    def add_entry(
        self,
        graph: Graph,
        vocabulary: Namespace,
        concept_uri: URIRef,
        entry: dict[str, Any],
    ) -> None:
        """Place the concept as a top concept and match it to its URL."""
        super().add_entry(graph, vocabulary, concept_uri, entry)

        url = entry.get("props", {}).get("url")
        if url:
            graph.add((concept_uri, SKOS.exactMatch, URIRef(url)))


class LicensesMerger(CuratedVocabularyMerger):
    """Merge the curated Creative Commons fragment into the RDM licenses.

    Both the fragment (see
    :class:`~.curated.CuratedVocabularyReader`) and the fixture emit their
    concepts into the same NMA licenses namespace, so the concepts are
    matched by URI: the RDM licenses are enriched with their Czech labels
    and placed below their version containers, the containers the RDM
    fixture does not carry are created. An untyped subject of the fragment
    that is no RDM license fails the merge - the fragment has gone stale.
    """

    vocabulary_type: ClassVar[str] = "licenses"

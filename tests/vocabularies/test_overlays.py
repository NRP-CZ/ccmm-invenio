#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests of the curated prop overlays of the data directory."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest
from rdflib import RDF, SKOS, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import PROPS_NAMESPACE
from ccmm_invenio.fixtures.compiler.merger import MappingsMerger
from ccmm_invenio.fixtures.compiler.readers import (
    OverlayReader,
    RDMDateTypesReader,
    RDMResourceTypesReader,
    RDMRolesReader,
    RDMTitleTypesReader,
)
from ccmm_invenio.fixtures.compiler.readers.rdm_fixture import (
    RDMFixtureReader,
)

DATA_DIR = Path(files("ccmm_invenio.fixtures.input.vocabularies"))


class RDMRelationTypesReader(RDMFixtureReader):
    """A reader for the InvenioRDM relation types fixture, for offline tests.

    The converter builds the relation types from the DataCite and CCMM
    vocabularies (both fetched over the network), so it has no fixture
    reader of its own; the fixture carries the same concepts as the DataCite
    vocabulary the converter merges, so it serves as the offline target of
    the relation types overlay here.
    """

    fixture_name = "relation_types.yaml"
    vocabulary_type = "relationtypes"


# the offline target vocabularies of the overlays: their RDM fixture readers
# (or the equivalent above), which the concepts of the overlays are a subset
# of (the vocabulary the converter builds is a superset of the fixture one)
OVERLAY_TARGETS = {
    "datetypes": RDMDateTypesReader,
    "relationtypes": RDMRelationTypesReader,
    "resourcetypes": RDMResourceTypesReader,
    "roles": RDMRolesReader,
    "titletypes": RDMTitleTypesReader,
}


@pytest.mark.parametrize(("overlay", "target"), OVERLAY_TARGETS.items())
def test_overlay_merges_into_its_vocabulary(overlay, target):
    """Every overlay subject is a concept of its target vocabulary."""
    overlay_graph = OverlayReader(DATA_DIR / f"{overlay}.ttl").read()
    graph = target("uri:does_not_matter").read()
    MappingsMerger(overlay_graph, graph).merge()

    # every overlay triple has landed in the vocabulary graph
    for triple in overlay_graph:
        assert triple in graph


def test_overlay_props():
    """The props of the overlays are the interoperability types."""
    roles = RDMRolesReader("uri:does_not_matter").read()
    MappingsMerger(OverlayReader(DATA_DIR / "roles.ttl").read(), roles).merge()

    datamanager = URIRef("https://nma.eosc.cz/vocabularies/roles/datamanager")
    assert (datamanager, PROPS_NAMESPACE["openaire"], Literal("DataManager")) in roles

    relationtypes = RDMRelationTypesReader("uri:does_not_matter").read()
    MappingsMerger(OverlayReader(DATA_DIR / "relationtypes.ttl").read(), relationtypes).merge()

    iscitedby = URIRef("https://nma.eosc.cz/vocabularies/relationtypes/iscitedby")
    assert (iscitedby, PROPS_NAMESPACE["zenodo"], Literal("iscitedby")) in relationtypes
    assert (iscitedby, PROPS_NAMESPACE["openaire"], Literal("IsCitedBy")) in relationtypes

    resourcetypes = RDMResourceTypesReader("uri:does_not_matter").read()
    MappingsMerger(OverlayReader(DATA_DIR / "resourcetypes.ttl").read(), resourcetypes).merge()

    dissertation = URIRef("https://nma.eosc.cz/vocabularies/resourcetypes/publication-dissertation")
    zenodo = {str(value) for value in resourcetypes.objects(dissertation, PROPS_NAMESPACE["zenodo"])}
    assert zenodo == {
        "publication-bachelorthesis",
        "publication-mastersthesis",
        "publication-doctorthesis",
        "publication-thesis",
        "publication-dissertation",
    }


def test_overlay_rejects_foreign_predicate(tmp_path):
    """A predicate outside the prop and tag namespaces fails the read."""
    overlay = tmp_path / "overlay.ttl"
    overlay.write_text(
        '<https://nma.eosc.cz/vocabularies/roles/editor> <http://example.org/props/not-a-prop> "nope" .\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not a prop or tag predicate"):
        OverlayReader(overlay).read()


def test_overlay_rejects_typed_literal(tmp_path):
    """A value that is not a plain literal fails the read."""
    overlay = tmp_path / "overlay.ttl"
    overlay.write_text(
        "<https://nma.eosc.cz/vocabularies/roles/editor>"
        " <https://nma.eosc.cz/vocabularies/vocabularies/inveniopropsopenaire>"
        " 42 .\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not a plain literal"):
        OverlayReader(overlay).read()


def test_overlay_subjects_are_not_concepts():
    """The overlay graphs carry no concept types - the vocabulary adds them.

    The access rights overlay has no offline target (its concepts come from
    the COAR vocabulary over the network), so it is tested for its reader
    validation only: reading it through :class:`OverlayReader` checks its
    predicates and values the same way as for the other overlays.
    """
    for overlay in [*OVERLAY_TARGETS, "accessrights"]:
        graph = OverlayReader(DATA_DIR / f"{overlay}.ttl").read()
        assert len(graph) > 0
        assert not set(graph.subjects(RDF.type, SKOS.Concept))


def test_access_rights_openaire():
    """The openaire access regime of the access rights, metadata-only is closedAccess as in InvenioRDM."""
    graph = OverlayReader(DATA_DIR / "accessrights.ttl").read()
    access_rights = "https://nma.eosc.cz/vocabularies/accessrights/"
    assert {
        str(subject).removeprefix(access_rights): str(value)
        for subject, value in graph.subject_objects(PROPS_NAMESPACE["openaire"])
    } == {
        "open": "info:eu-repo/semantics/openAccess",
        "embargoed": "info:eu-repo/semantics/embargoedAccess",
        "restricted": "info:eu-repo/semantics/restrictedAccess",
        "metadata-only": "info:eu-repo/semantics/closedAccess",
    }

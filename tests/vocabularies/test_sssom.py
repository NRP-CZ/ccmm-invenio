#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest
import yaml
from rdflib import RDF, SKOS, Graph, URIRef

from ccmm_invenio.fixtures.compiler.merger import MappingsMerger
from ccmm_invenio.fixtures.compiler.readers import (
    RDMResourceTypesReader,
    SSSOMMappingsReader,
)

DATA_DIR = Path(files("ccmm_invenio.fixtures.input.vocabularies"))
NMA_RESOURCE_TYPE = URIRef("https://nma.eosc.cz/vocabularies/resourcetypes/dataset")
COAR_DATASET = URIRef("http://purl.org/coar/resource_type/c_ddb1")


def test_sssom_reader_expands_curies():
    """The mappings become triples of expanded subject and object URIs."""
    graph = SSSOMMappingsReader(DATA_DIR / "resource_types.yaml").read()

    # the 42 mapped entries of the 47 (5 carry no counterpart, only comments)
    assert len(graph) == 42
    assert (NMA_RESOURCE_TYPE, SKOS.exactMatch, COAR_DATASET) in graph

    # every subject and object is a URI, every predicate a SKOS mapping property
    predicates = {SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch, SKOS.narrowMatch, SKOS.relatedMatch}
    for subject, predicate, triple_object in graph:
        assert isinstance(subject, URIRef)
        assert isinstance(triple_object, URIRef)
        assert predicate in predicates


def test_sssom_reader_rejects_unknown_identifier():
    """Identifiers outside the curie map fail instead of passing through."""
    reader = SSSOMMappingsReader("unused")
    with pytest.raises(ValueError, match="neither a URI nor a CURIE"):
        reader.expand("no_such_prefix:dataset", {"nma_resourcetypes": "https://x/"})
    with pytest.raises(ValueError, match="SKOS mapping property"):
        reader.predicate("owl:sameAs", {})


def test_mappings_merger_enriches_resource_types():
    """The mapping overlays are merged into the RDM resource types."""
    vocabulary = RDMResourceTypesReader().read()
    mappings = SSSOMMappingsReader(DATA_DIR / "resource_types.yaml").read()
    assert (NMA_RESOURCE_TYPE, SKOS.exactMatch, COAR_DATASET) not in vocabulary

    merged = MappingsMerger(mappings, vocabulary).merge()

    assert merged is vocabulary
    assert (NMA_RESOURCE_TYPE, SKOS.exactMatch, COAR_DATASET) in vocabulary


def test_mappings_merger_rejects_stale_subject():
    """A mapping of a concept the target does not know fails the merge."""
    vocabulary = Graph()
    vocabulary.add((NMA_RESOURCE_TYPE, RDF.type, SKOS.Concept))

    mappings = Graph()
    stale = URIRef("https://nma.eosc.cz/vocabularies/resourcetypes/renamed-away")
    mappings.add((stale, SKOS.exactMatch, COAR_DATASET))

    with pytest.raises(KeyError, match="stale"):
        MappingsMerger(mappings, vocabulary).merge()
    assert len(vocabulary) == 1  # nothing but the original concept


def test_resourcetypes_export_carries_coar_mappings(tmp_path):
    """The wired converter exports the COAR mappings of the resource types."""
    from ccmm_invenio.fixtures.compiler.converter import vocabulary_builders
    from ccmm_invenio.fixtures.compiler.invenio_export import export_vocabulary

    export_vocabulary(vocabulary_builders()["resourcetypes"](), tmp_path / "resourcetypes.yaml")
    entries = {entry["id"]: entry for entry in yaml.safe_load((tmp_path / "resourcetypes.yaml").read_text())}

    assert {
        "identifier": str(COAR_DATASET),
        "scheme": "http://purl.org/coar/resource_type/",
        "relation": "exactMatch",
    } in entries["dataset"]["mappings"]
    # the unmapped types stay in the vocabulary, just without COAR mappings
    assert "event" in entries
    assert not any(
        mapping["scheme"] == "http://purl.org/coar/resource_type/" for mapping in entries["event"].get("mappings", [])
    )

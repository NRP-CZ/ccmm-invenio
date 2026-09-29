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

import pytest
import yaml
from rdflib import RDF, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import NOTATION_ID_DATATYPE
from ccmm_invenio.fixtures.compiler.invenio_export import (
    export_vocabulary,
    topological_order,
)
from ccmm_invenio.fixtures.compiler.readers import RDMLicensesReader


def make_concept(graph: Graph, uri: str, entry_id_: str, parent: str | None = None) -> URIRef:
    """Add a concept with an id notation and an optional broader link."""
    concept = URIRef(uri)
    graph.add((concept, RDF.type, SKOS.Concept))
    graph.add((concept, SKOS.notation, Literal(entry_id_, datatype=NOTATION_ID_DATATYPE)))
    if parent:
        graph.add((concept, SKOS.broader, URIRef(parent)))
    return concept


def test_export_vocabulary_roundtrip(tmp_path):
    """The licenses fixture survives the detour through graph and export."""
    reader = RDMLicensesReader("uri:does_not_matter")
    graph = reader.read()

    # the semantic declarations are not concepts and are not exported
    assert len(set(graph.subjects(RDF.type, SKOS.Concept))) == 419

    output_path = tmp_path / "licenses.yaml"
    export_vocabulary(graph, output_path)
    exported = {entry["id"]: entry for entry in yaml.safe_load(output_path.read_text())}

    assert len(exported) == 419
    original = reader.load_entries(files("invenio_rdm_records.fixtures.data.vocabularies") / "licenses.csv")
    assert len(original) == 419

    for entry in original:
        exported_entry = exported[entry["id"]]

        # the entries keep their ids, labels, descriptions and tags (the
        # empty descriptions of the csv are dropped, not exported as '')
        assert exported_entry.get("title") == entry.get("title")
        assert exported_entry.get("description") == entry.get("description") or (
            not any(entry.get("description", {}).values())
        )
        assert sorted(exported_entry.get("tags", [])) == sorted(entry.get("tags", []))

        # the props keep their fixture names; empty ones are not exported
        assert exported_entry.get("props", {}) == {
            name: value for name, value in entry.get("props", {}).items() if value
        }


def test_export_vocabulary_mappings(tmp_path):
    """The mapping links of concepts become the entry mappings."""
    graph = RDMLicensesReader("uri:does_not_matter").read()

    output_path = tmp_path / "licenses.yaml"
    export_vocabulary(graph, output_path)
    exported = {entry["id"]: entry for entry in yaml.safe_load(output_path.read_text())}

    # the exact match to the license URL is serialized as its mapping,
    # under the enclosing namespace of the URL
    assert exported["mit"]["mappings"] == [
        {
            "identifier": "https://opensource.org/license/mit",
            "scheme": "https://opensource.org/license/",
            "relation": "exactMatch",
        }
    ]
    assert exported["cc-by-4.0"]["mappings"] == [
        {
            "identifier": "https://creativecommons.org/licenses/by/4.0/",
            "scheme": "https://creativecommons.org/licenses/by/4.0/",
            "relation": "exactMatch",
        }
    ]


def test_export_vocabulary_hierarchy(tmp_path):
    """The broader links become the entry hierarchy, parents first."""
    graph = Graph()
    namespace = "https://nma.eosc.cz/vocabularies/test/"
    make_concept(graph, namespace + "parent", "parent")
    make_concept(graph, namespace + "child", "child", namespace + "parent")
    make_concept(graph, namespace + "grandchild", "grandchild", namespace + "child")
    # a broader link outside the vocabulary is no parent of the entry
    orphan = make_concept(graph, namespace + "orphan", "orphan")
    graph.add((orphan, SKOS.broader, URIRef("https://example.org/elsewhere")))

    output_path = tmp_path / "test.yaml"
    export_vocabulary(graph, output_path)
    entries = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    by_id = {entry["id"]: entry for entry in entries}
    assert by_id["child"]["hierarchy"] == {"parent": "parent"}
    assert by_id["grandchild"]["hierarchy"] == {"parent": "child"}
    assert "hierarchy" not in by_id["parent"]
    assert "hierarchy" not in by_id["orphan"]

    # every parent precedes its children in the exported list
    positions = {entry["id"]: position for position, entry in enumerate(entries)}
    assert positions["parent"] < positions["child"] < positions["grandchild"]


def test_export_vocabulary_cycle(tmp_path):
    """A cycle in the hierarchy fails the export instead of hanging it."""
    graph = Graph()
    namespace = "https://nma.eosc.cz/vocabularies/test/"
    make_concept(graph, namespace + "one", "one", namespace + "two")
    make_concept(graph, namespace + "two", "two", namespace + "one")

    with pytest.raises(ValueError, match="cycle"):
        export_vocabulary(graph, tmp_path / "test.yaml")


def test_topological_order_keeps_sorted_order_of_flat_entries():
    """Entries without a hierarchy keep their (sorted) incoming order."""
    entries = [{"id": id_} for id_ in ["c", "a", "b"]]
    assert topological_order(entries) == entries


def test_topological_order_sorts_parents_before_children():
    """Children wait for their parents but keep the sorted order among them."""
    entries = [
        {"id": "a", "hierarchy": {"parent": "z"}},
        {"id": "b", "hierarchy": {"parent": "a"}},
        {"id": "c"},
        {"id": "z"},
    ]
    assert topological_order(entries) == [
        {"id": "c"},
        {"id": "z"},
        {"id": "a", "hierarchy": {"parent": "z"}},
        {"id": "b", "hierarchy": {"parent": "a"}},
    ]

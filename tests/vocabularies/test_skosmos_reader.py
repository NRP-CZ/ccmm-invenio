#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from rdflib import RDF, SKOS, Graph

from ccmm_invenio.fixtures.compiler.readers import SkosmosReader

CODELIST_URI = "https://vocabs.ccmm.cz/registry/codelist/RelationType/"


def test_skosmos_data_url():
    reader = SkosmosReader(CODELIST_URI)

    assert reader.data_url() == (
        "https://vocabs.ccmm.cz/rest/v1/RelationType/data"
        "?uri=https%3A%2F%2Fvocabs.ccmm.cz%2Fregistry%2Fcodelist%2FRelationType%2F"
        "&format=text/turtle"
    )


def test_skosmos_data_url_without_trailing_slash():
    reader = SkosmosReader("https://vocabs.ccmm.cz/registry/codelist/RelationType")

    assert reader.data_url() == (
        "https://vocabs.ccmm.cz/rest/v1/RelationType/data"
        "?uri=https%3A%2F%2Fvocabs.ccmm.cz%2Fregistry%2Fcodelist%2FRelationType"
        "&format=text/turtle"
    )


def test_skosmos_read_loads_rdf_from_rest_url(monkeypatch):
    parsed = []

    def fake_parse(self, source: str, **kwargs: object) -> Graph:
        parsed.append(source)
        self.add((SKOS.ConceptScheme, RDF.type, SKOS.ConceptScheme))
        return self

    monkeypatch.setattr(Graph, "parse", fake_parse)

    reader = SkosmosReader(CODELIST_URI)
    graph = reader.read()

    assert parsed == [reader.data_url()]
    assert (SKOS.ConceptScheme, RDF.type, SKOS.ConceptScheme) in graph

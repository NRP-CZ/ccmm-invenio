#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
# the tests look into the private methods of the merger on purpose
# ruff: noqa: SLF001

from __future__ import annotations

from rdflib import RDF, SKOS, Graph, Literal, Namespace

from ccmm_invenio.fixtures.compiler.constants import PROPS_NAMESPACE, TAGS_URI
from ccmm_invenio.fixtures.compiler.merger import VocabularyMerger

SOURCE = Namespace("https://example.org/source/")
TARGET = Namespace("https://example.org/target/")


class LabelMerger(VocabularyMerger):
    """Merge prefLabels into altLabels, drop everything else."""

    def find_in_target(self, source_concept_uri):
        """Return the concept of the same local name when it exists."""
        target_uri = TARGET[str(source_concept_uri).rsplit("/", 1)[-1]]
        return target_uri if (target_uri, None, None) in self.target_graph else None

    def transform_predicate(self, predicate_name, value):
        """Turn prefLabels into altLabels, keep the type, drop the rest."""
        if predicate_name == SKOS.prefLabel:
            return [(SKOS.altLabel, value)]
        if predicate_name == RDF.type:
            return [(RDF.type, value)]
        return []


class SingleValuedLabelMerger(LabelMerger):
    """Like LabelMerger, but the merged altLabel is single valued."""

    single_valued_predicates = frozenset({SKOS.altLabel})


def make_source():
    graph = Graph()
    graph.add((SOURCE.A, RDF.type, SKOS.Concept))
    graph.add((SOURCE.A, SKOS.prefLabel, Literal("taken", lang="en")))
    graph.add((SOURCE.A, SKOS.prefLabel, Literal("taken")))  # variant of "taken"@en
    graph.add((SOURCE.A, SKOS.prefLabel, Literal("nový", lang="cs")))
    graph.add((SOURCE.A, SKOS.definition, Literal("dropped")))
    graph.add((SOURCE.B, RDF.type, SKOS.Concept))
    graph.add((SOURCE.B, SKOS.prefLabel, Literal("no counterpart", lang="en")))
    return graph


def make_target():
    graph = Graph()
    graph.add((TARGET.A, RDF.type, SKOS.Concept))
    graph.add((TARGET.A, SKOS.altLabel, Literal("taken", lang="en")))
    return graph


def test_merge():
    target = make_target()
    merger = LabelMerger(SOURCE, make_source(), TARGET, target)

    assert merger.merge() is target

    # exact match and language variant of "taken" are not merged,
    # the new string is - and it keeps its language
    alt_labels = sorted(target.objects(TARGET.A, SKOS.altLabel), key=str)
    assert alt_labels == [Literal("nový", lang="cs"), Literal("taken", lang="en")]

    # transformed predicates not returned by transform_predicate are dropped
    assert (TARGET.A, SKOS.definition, None) not in target

    # concepts without a counterpart in the target are skipped
    assert (TARGET.B, None, None) not in target


def test_merge_add_missing():
    target = make_target()
    merger = LabelMerger(SOURCE, make_source(), TARGET, target)

    merger.merge(add_missing=True)

    # the counterpart is merged as usual
    alt_labels = sorted(target.objects(TARGET.A, SKOS.altLabel), key=str)
    assert alt_labels == [Literal("nový", lang="cs"), Literal("taken", lang="en")]

    # the missing concept is created in the target namespace
    assert (TARGET.B, SKOS.altLabel, Literal("no counterpart", lang="en")) in target
    assert (TARGET.B, RDF.type, SKOS.Concept) in target


def test_is_single_valued_defaults():
    merger = LabelMerger(SOURCE, make_source(), TARGET, make_target())

    # one label per language, one notation per datatype
    assert merger._is_single_valued(SKOS.prefLabel)
    assert merger._is_single_valued(SKOS.notation)

    # every prop is single valued, without enumerating them
    assert merger._is_single_valued(PROPS_NAMESPACE.datacite)
    assert merger._is_single_valued(PROPS_NAMESPACE.xml_lang)
    assert merger._is_single_valued(PROPS_NAMESPACE.alpha_2)

    # the additive ones stay additive
    assert not merger._is_single_valued(SKOS.exactMatch)
    assert not merger._is_single_valued(TAGS_URI)
    assert not merger._is_single_valued(SKOS.altLabel)


def test_source_concepts_only_from_source_namespace():
    graph = make_source()
    graph.add((SOURCE[""], RDF.type, SKOS.ConceptScheme))  # the scheme itself

    merger = LabelMerger(SOURCE, graph, TARGET, make_target())
    assert merger._source_concepts() == sorted([SOURCE.A, SOURCE.B, SOURCE[""]])


def test_merge_single_valued_per_language():
    target = Graph()
    target.add((TARGET.A, RDF.type, SKOS.Concept))
    target.add((TARGET.A, SKOS.altLabel, Literal("old en", lang="en")))
    target.add((TARGET.A, SKOS.altLabel, Literal("stará", lang="cs")))

    source = Graph()
    source.add((SOURCE.A, RDF.type, SKOS.Concept))
    source.add((SOURCE.A, SKOS.prefLabel, Literal("new en", lang="en")))
    source.add((SOURCE.A, SKOS.prefLabel, Literal("nová", lang="cs")))

    merger = SingleValuedLabelMerger(SOURCE, source, TARGET, target)
    merger.merge()

    # one value per language, the source winning
    assert set(target.objects(TARGET.A, SKOS.altLabel)) == {
        Literal("new en", lang="en"),
        Literal("nová", lang="cs"),
    }


def test_merge_single_valued_plain_replaces_all():
    target = Graph()
    target.add((TARGET.A, RDF.type, SKOS.Concept))
    target.add((TARGET.A, SKOS.altLabel, Literal("old en", lang="en")))
    target.add((TARGET.A, SKOS.altLabel, Literal("stará", lang="cs")))

    source = Graph()
    source.add((SOURCE.A, RDF.type, SKOS.Concept))
    source.add((SOURCE.A, SKOS.prefLabel, Literal("plain")))  # untagged

    merger = SingleValuedLabelMerger(SOURCE, source, TARGET, target)
    merger.merge()

    # a plain value has no language or datatype - it replaces all of them
    assert set(target.objects(TARGET.A, SKOS.altLabel)) == {Literal("plain")}

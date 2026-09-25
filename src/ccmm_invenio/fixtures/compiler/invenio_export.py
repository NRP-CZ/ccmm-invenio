#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Export of vocabulary graphs into Invenio vocabulary fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from rdflib import RDF, SKOS, Graph, Literal, URIRef

from .constants import (
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    SKOS_MAPPING_PROPERTIES,
    TAGS_URI,
)

PROPS_VALUE_SEPARATOR = ", "
"""Separator of the values of a multi-valued prop in a fixture entry.

Props are single strings in Invenio; a prop carrying several values (e.g.
several codes of the same notation scheme) is joined into one string.
"""

MATCH_RELATIONS: dict[URIRef, str] = {
    mapping_property: name for name, mapping_property in SKOS_MAPPING_PROPERTIES.items()
}
"""The SKOS mapping properties and their oarepo-vocabularies relations.

The mapping links of the concepts (the ``skos:exactMatch`` IRIs of
the source concepts, e.g. the CCMM codelist or the IANA registry entry a
concept was read from) are serialized as the ``mappings`` of the fixture
entries, so that a record carrying the source IRI resolves to the item.
"""


def export_vocabulary(graph: Graph, output_path: Path) -> None:
    """Export a vocabulary graph as an Invenio vocabulary fixture.

    Every ``skos:Concept`` of the graph becomes one fixture entry
    (see :func:`vocabulary_entry`); the entries are written as a YAML list
    into ``output_path``, ordered by their ids for reproducible outputs -
    except that the children of a hierarchical vocabulary follow their
    parents (see :func:`topological_order`), as the fixture loader needs the
    parent of an entry to be loaded before the entry itself.
    The format is the one the ``invenio_vocabularies`` fixtures read and
    :class:`~ccmm_invenio.fixtures.compiler.readers.RDMFixtureReader`
    mirrors, so a vocabulary round-trips between its graph and its fixture.

    Not everything of the graph survives the export: the fixture entries
    carry only the entry fields Invenio knows (labels, definitions, tags,
    props, mappings, hierarchy), so e.g. ``skos:altLabel`` is dropped.

    Args:
        graph: the vocabulary graph to export
        output_path: path of the YAML fixture file to write

    """
    entries = [
        vocabulary_entry(graph, concept)
        for concept in sorted(
            (concept for concept in graph.subjects(RDF.type, SKOS.Concept) if isinstance(concept, URIRef)),
            key=lambda concept: entry_id(graph, concept),
        )
    ]
    entries = topological_order(entries)
    with Path(output_path).open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(
            entries,
            output_file,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def export_subjects(graph: Graph, output_path: Path, scheme: str) -> None:
    """Export a subjects graph as an Invenio subjects fixture.

    Every ``skos:Concept`` of the graph becomes one subject entry
    (see :func:`subject_entry`); the entries are written as a YAML list
    into ``output_path``, ordered by their ids for reproducible outputs.
    The format is the one the subjects datastream of ``invenio_vocabularies``
    reads and the subjects service validates (the ``subjects`` variant of
    :class:`invenio_vocabularies.services.schema.BaseVocabularySchema`):
    the scheme-prefixed classification code as the globally unique ``id``
    (e.g. ``ford:10101``), the scheme it classifies under and the labels.

    Not everything of the graph survives the export: the subject entries
    carry only the subject fields (id, scheme, subject, title, synonyms,
    props, identifiers, tags), so e.g. the definitions of the concepts and
    the scheme structure are dropped - they do not fit the subjects model
    of invenio (the hierarchy survives as the ``parents`` prop carrying the
    id of the parent concept, the way the invenio subject transformers of
    GEMET and EuroSciVoc serialize it).

    Args:
        graph: the subjects graph to export
        output_path: path of the YAML fixture file to write
        scheme: the scheme identifier the subjects classify under
            (e.g. ``FORD``, see
            :data:`~ccmm_invenio.fixtures.compiler.readers.SUBJECT_SCHEME`)

    """
    entries = [
        subject_entry(graph, concept, scheme)
        for concept in sorted(
            (concept for concept in graph.subjects(RDF.type, SKOS.Concept) if isinstance(concept, URIRef)),
            key=lambda concept: entry_id(graph, concept),
        )
    ]
    with Path(output_path).open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(
            entries,
            output_file,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def subject_entry(graph: Graph, concept: URIRef, scheme: str) -> dict:
    """Build the fixture entry of a subject concept.

    The entry carries the id notation as the ``id`` and the prefLabels as
    the language-keyed ``title`` map; the English label is the ``subject``,
    the primary string the subjects service sorts and suggests by (the
    first title when there is no English one). The altLabels become the
    ``synonyms``. The props of the concept (see :func:`concept_props`, e.g. the
    ``classification_code``) are the ``props``; the hierarchy is carried by the ``parents`` prop - the
    entry id of the parent concept, single level (a UI picks the parent to
    browse into, not the whole ancestor chain) - and the mapping links to
    the authority IRIs (the ``skos:exactMatch`` links) become the URL
    ``identifiers``.

    Args:
        graph: the subjects graph the concept is read from
        concept: the concept URI to build the entry of
        scheme: the scheme identifier the subjects classify under

    """
    entry: dict[str, Any] = {
        "id": entry_id(graph, concept),
        "scheme": scheme,
    }

    if titles := i18n_strings(graph, concept, SKOS.prefLabel):
        entry["title"] = titles
        entry["subject"] = titles.get("en") or next(iter(titles.values()))

    if synonyms := sorted({str(label) for label in graph.objects(concept, SKOS.altLabel)}):
        entry["synonyms"] = synonyms

    # the props (e.g. the classification_code) and the parent concept as the parents prop
    props = concept_props(graph, concept)
    if parent := concept_parent(graph, concept):
        props["parents"] = parent
    if props:
        entry["props"] = props

    if identifiers := subject_identifiers(graph, concept):
        entry["identifiers"] = identifiers

    return entry


def subject_identifiers(graph: Graph, concept: URIRef) -> list[dict[str, str]]:
    """Collect the URL identifiers of a subject: its authority links.

    A mapping link of the concept (see :data:`MATCH_RELATIONS`) points at
    the authority concept the subject was read from; only the
    ``skos:exactMatch`` links carry the authority of the source, the
    other ones map to foreign vocabularies instead. The URLs are one of
    the identifier schemes the subjects service allows.
    """
    return [
        {"scheme": "url", "identifier": str(identifier)}
        for identifier in sorted(graph.objects(concept, SKOS.exactMatch), key=str)
        if isinstance(identifier, URIRef)
    ]


def vocabulary_entry(graph: Graph, concept: URIRef) -> dict:
    """Build the fixture entry of a vocabulary concept.

    The entry carries the id notation as the ``id``, the prefLabels and
    definitions as language-keyed ``title`` and ``description`` maps (labels
    without a language end up under ``en``), the parent concept as the
    ``hierarchy.parent`` (see :func:`concept_parent`), the tag values as
    ``tags`` and the props as ``props``. The props collect the values of the
    :data:`PROPS_NAMESPACE` predicates (under their prop names) together
    with the foreign ``skos:notation`` values, keyed by their notation
    datatypes (e.g. the euvoc ISO 639-1 codes of a language or the IANA
    media type of a file format) - both are needed to map records back and
    forth, so they must survive the export. The mapping links of the concept
    (see :data:`MATCH_RELATIONS`) are serialized as its ``mappings``.

    Args:
        graph: the vocabulary graph the concept is read from
        concept: the concept URI to build the entry of

    """
    entry: dict[str, Any] = {"id": entry_id(graph, concept)}

    if titles := i18n_strings(graph, concept, SKOS.prefLabel):
        entry["title"] = titles

    if descriptions := i18n_strings(graph, concept, SKOS.definition):
        entry["description"] = descriptions

    if parent := concept_parent(graph, concept):
        entry["hierarchy"] = {"parent": parent}

    if tags := sorted({str(tag) for tag in graph.objects(concept, TAGS_URI)}):
        entry["tags"] = tags

    if props := concept_props(graph, concept):
        entry["props"] = props

    if mappings := concept_mappings(graph, concept):
        entry["mappings"] = mappings

    return entry


def concept_parent(graph: Graph, concept: URIRef) -> str | None:
    """Return the entry id of the parent of a concept, if it has one.

    The parent is the concept the concept hangs below via
    ``skos:broader``; only the broader concepts that are concepts of the
    same graph count - a broader link to anything else (a concept of another
    vocabulary, a concept scheme, ...) is no parent of the entry, the fixture
    entries cannot reference it. With several such parents the first one by
    its URI wins, so that the parent stays deterministic.

    Args:
        graph: the vocabulary graph the concept is read from
        concept: the concept URI to return the parent of

    """
    parents = sorted(
        broader
        for broader in graph.objects(concept, SKOS.broader)
        if isinstance(broader, URIRef) and (broader, RDF.type, SKOS.Concept) in graph
    )
    return entry_id(graph, parents[0]) if parents else None


def topological_order(entries: list[dict]) -> list[dict]:
    """Order fixture entries so that every parent precedes its children.

    The entries come in the sorted order of their ids; the ones whose parent
    (their ``hierarchy.parent``) has not been ordered yet wait for the next
    round, until all of them are ordered. The rounds keep the sorted order of
    the entries, so the result stays deterministic - and is the very sorted
    order the entries came in, for a vocabulary without a hierarchy.

    A cycle in the hierarchy - an entry (directly or transitively) its own
    parent - never becomes ready; it fails the export instead of ending up in
    an order the fixture loader cannot load.

    Args:
        entries: the fixture entries, sorted by their ids

    Returns:
        the entries, every parent before its children

    """
    ordered: list[dict] = []
    ordered_ids: set[str] = set()
    remaining = entries
    while remaining:
        ready = [
            entry
            for entry in remaining
            if (parent := entry.get("hierarchy", {}).get("parent")) is None or parent in ordered_ids
        ]
        if not ready:
            raise ValueError(
                "the vocabulary hierarchy has a cycle, please check the data: "
                f"{sorted(entry['id'] for entry in remaining)}"
            )
        ordered.extend(ready)
        ready_ids = {entry["id"] for entry in ready}
        ordered_ids.update(ready_ids)
        remaining = [entry for entry in remaining if entry["id"] not in ready_ids]
    return ordered


def i18n_strings(graph: Graph, concept: URIRef, predicate: URIRef) -> dict[str, str]:
    """Collect the language-keyed strings of a concept predicate.

    Literals without a language are collected under ``en`` - the fixtures
    need a language key, and the plain literals of our vocabularies are
    unlabeled English texts; empty strings are dropped, an empty label or
    description is no label or description at all. The strings are collected
    in sorted order, so that the maps (and with them the exported fixtures)
    are deterministic - their plain iteration order would vary with the hash
    seed of the run. With several values of one language, the lexically
    last one in the sorted order wins.
    """
    return dict(
        sorted(
            (value.language or "en", str(value))
            for value in graph.objects(concept, predicate)
            if isinstance(value, Literal) and str(value)
        )
    )


def concept_props(graph: Graph, concept: URIRef) -> dict[str, str]:
    """Collect the props of a concept.

    The props of a concept are the values of its :data:`PROPS_NAMESPACE`
    predicates (keyed by their prop names) and the values of its foreign
    ``skos:notation`` notations (keyed by their datatype names, e.g.
    ``ISO_639_1`` for euvoc ISO 639-1 codes); the id notation is the entry
    id and is not repeated as a prop. A prop with several values carries
    them joined with :data:`PROPS_VALUE_SEPARATOR`.
    """
    values: dict[str, list[str]] = {}

    for predicate, value in graph.predicate_objects(concept):
        if str(predicate).startswith(str(PROPS_NAMESPACE)):
            name = str(predicate)[len(str(PROPS_NAMESPACE)) :]
        elif predicate == SKOS.notation and isinstance(value, Literal):
            if value.datatype in (None, NOTATION_ID_DATATYPE):
                continue
            name = datatype_name(value.datatype)
        else:
            continue
        values.setdefault(name, []).append(str(value))

    return {name: PROPS_VALUE_SEPARATOR.join(sorted(set(prop_values))) for name, prop_values in sorted(values.items())}


def datatype_name(datatype: URIRef) -> str:
    """Return the name of a notation datatype.

    The notation scheme of a ``skos:notation`` literal is identified by
    its datatype URI; its name is the URI's fragment, or its last path
    segment for hashless URIs (e.g. ``.../euvoc#ISO_639_1`` ->
    ``ISO_639_1``).
    """
    return str(datatype).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def concept_mappings(graph: Graph, concept: URIRef) -> list[dict[str, str]]:
    """Collect the mappings of a concept.

    A mapping link of the concept (see :data:`MATCH_RELATIONS`) becomes a
    mapping of the matched IRI under its enclosing namespace: the IRI up
    to and including its last separator (``/`` or ``#``), which is the
    namespace the mapped item lives in - e.g. the IANA media type
    ``http://www.iana.org/assignments/media-types/application/pdf`` is
    mapped with the scheme
    ``http://www.iana.org/assignments/media-types/``.
    """
    mappings = [
        {
            "identifier": str(identifier),
            "scheme": enclosing_namespace(str(identifier)),
            "relation": relation,
        }
        for predicate, relation in sorted(MATCH_RELATIONS.items(), key=str)
        for identifier in graph.objects(concept, predicate)
        if isinstance(identifier, URIRef)
    ]
    return sorted(
        mappings,
        key=lambda mapping: (
            mapping["identifier"],
            mapping["scheme"],
            mapping["relation"],
        ),
    )


def enclosing_namespace(identifier: str) -> str:
    """Return the enclosing namespace of an identifier.

    The namespace is the identifier up to and including its last ``/`` or
    ``#``, whichever comes last - the part an item of the namespace is
    appended to (e.g. ``.../media-types/`` of
    ``.../media-types/application/pdf``). An identifier that is nothing but
    its namespace (e.g. ``https://orcid.org/``) is its own namespace.
    """
    return identifier[: max(identifier.rfind("/"), identifier.rfind("#")) + 1]


def entry_id(graph: Graph, concept: URIRef) -> str:
    """Return the entry id of a concept: its id notation.

    The readers mark the vocabulary entry id with the
    :data:`NOTATION_ID_DATATYPE` datatype, so that it can be told apart from
    the foreign notations. Unlike the concept URI, the notation keeps the
    whole id (e.g. ``application/pdf`` of a mediatype concept whose URI ends
    in ``.../mediatypes/application/pdf``).
    """
    return next(
        str(notation)
        for notation in graph.objects(concept, SKOS.notation)
        if isinstance(notation, Literal) and notation.datatype == NOTATION_ID_DATATYPE
    )

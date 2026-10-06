#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers for the language vocabularies."""

from __future__ import annotations

import gettext
from pathlib import Path
from typing import TYPE_CHECKING, override

import pycountry
from rdflib import RDF, SKOS, Graph, Literal

from ..constants import (
    EUROPA_LANGUAGE_NAMESPACE,
    EUVOC_NAMESPACE,
    MISSING_EUROPA_LANGUAGE_CODES,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    SUPPORTED_LABEL_LANGUAGES,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations
from .base import NO_SOURCE_URI, VocabularyReader

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


def _load_name_translations() -> dict[str, gettext.GNUTranslations]:
    """Load the ISO 639-3 language-name translations bundled with pycountry.

    pycountry ships the gettext catalogs of the Debian iso-codes project; the
    msgids are the English language names. Catalogs are keyed by their base
    language tag (regional variants such as ``bn_BD`` are folded into ``bn``).
    Only the supported label languages are loaded - the labels of the
    languages themselves are the bulk of the vocabulary, and carrying every
    translation pycountry ships would bloat it (see
    :data:`SUPPORTED_LABEL_LANGUAGES`).
    """
    locales = sorted(
        path
        for path in Path(pycountry.LOCALES_DIR).iterdir()
        if path.is_dir() and path.name.split("_")[0] in SUPPORTED_LABEL_LANGUAGES
    )
    translations: dict[str, gettext.GNUTranslations] = {}
    for path in locales:
        # skip script variants such as 'sr@latin' - the base locale is loaded anyway
        if "@" in path.name:
            continue
        tag = path.name.split("_")[0]
        if tag in translations:
            continue
        try:
            translations[tag] = gettext.translation("iso639-3", pycountry.LOCALES_DIR, languages=[path.name])
        except FileNotFoundError:
            continue
    return translations


class LanguageReader(VocabularyReader):
    """A reader for the ISO 639-3 languages.

    The source is pycountry (the Debian iso-codes data): every language
    becomes a concept under its ISO 639-3 code, with the English name as
    the prefLabel and the names of the supported label languages added
    through the iso-codes gettext catalogs (see
    :func:`_load_name_translations`). Each concept carries the ISO 639-1
    code and the xml:lang tag as props, the euvoc ISO 639-1, ISO 639-3 and
    XML_LNG notations, the scope and type tags, and a ``skos:exactMatch``
    link to its EU language authority counterpart (except for
    :data:`MISSING_EUROPA_LANGUAGE_CODES`).
    """

    scope_map: Mapping[str, str] = {
        "I": "individual",
        "M": "macrolanguage",
        "S": "special-scope",
    }

    type_map: Mapping[str, str] = {
        "A": "ancient",
        "C": "constructed",
        "E": "extinct",
        "H": "historical",
        "L": "living",
        "S": "special-type",
    }

    def __init__(self, uri: str = NO_SOURCE_URI):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the languages vocabulary graph from the pycountry data."""
        graph = Graph()
        graph += semantic_declarations()
        languages = make_vocabulary_namespace("languages")
        name_translations = _load_name_translations()

        for lang in pycountry.languages:
            # not every ISO 639-3 code exists in the EU language authority
            source_uri = (
                None
                if lang.alpha_3 in MISSING_EUROPA_LANGUAGE_CODES
                else EUROPA_LANGUAGE_NAMESPACE[lang.alpha_3.upper()]
            )
            # the concept URI uses the uppercase code; add_concept's
            # notation is lowercased, matching the YAML round-trip
            concept_uri = self.add_concept(graph, languages, lang.alpha_3.upper(), source_uri=source_uri)
            graph.add((concept_uri, SKOS.prefLabel, Literal(lang.name, lang="en")))
            for tag, catalog in name_translations.items():
                # gettext returns the msgid unchanged when there is no translation
                if (name := catalog.gettext(lang.name)) != lang.name:
                    graph.add((concept_uri, SKOS.prefLabel, Literal(name, lang=tag)))

            if alpha2 := getattr(lang, "alpha_2", ""):
                graph.add((concept_uri, PROPS_NAMESPACE.alpha_2, Literal(alpha2)))
                graph.add(
                    (
                        concept_uri,
                        SKOS.notation,
                        Literal(alpha2, datatype=EUVOC_NAMESPACE.ISO_639_1),
                    )
                )

            # IETF tag for xml:lang: prefer the ISO 639-1 code, fall back to 639-3
            xml_lang = getattr(lang, "alpha_2", "") or lang.alpha_3
            graph.add((concept_uri, PROPS_NAMESPACE.xml_lang, Literal(xml_lang)))

            # europa euvoc notation schemes we can derive from ISO data:
            # ISO_639_2B/2T and the application codes (TED, PLANJO, ...) would
            # need their own source tables
            graph.add(
                (
                    concept_uri,
                    SKOS.notation,
                    Literal(xml_lang, datatype=EUVOC_NAMESPACE.XML_LNG),
                )
            )
            graph.add(
                (
                    concept_uri,
                    SKOS.notation,
                    Literal(lang.alpha_3, datatype=EUVOC_NAMESPACE.ISO_639_3),
                )
            )

            graph.add((concept_uri, TAGS_URI, Literal(self.scope_map[lang.scope])))
            graph.add((concept_uri, TAGS_URI, Literal(self.type_map[lang.type])))
        return graph


EXTRA_PRIMARY_LANGUAGES = frozenset({"und"})
"""Primary languages without an ISO 639-1 code: ``und`` (Undetermined) - the language of a
text without one (``xml:lang=""`` in ccmm), stored in the multilingual fields that require a language."""


class PrimaryLanguagesReader(VocabularyReader):
    """A reader for the primary languages: the ISO 639-1 subset of the languages.

    The primary languages are the languages of the full vocabulary that
    carry an ISO 639-1 code - the short list the deposit forms offer - and the
    :data:`EXTRA_PRIMARY_LANGUAGES`. The
    concepts are read from the graph ``graph_builder`` returns - the whole
    language vocabulary of a :class:`LanguageReader`, parsed once and shared
    with its own export. It is called lazily, from :meth:`read`, so that
    constructing the reader does not build it.
    """

    def __init__(self, graph_builder: Callable[[], Graph]):
        """Initialize the reader with the full language vocabulary builder.

        Args:
            graph_builder: a zero-argument callable returning the graph
                read by :class:`LanguageReader`

        """
        super().__init__(NO_SOURCE_URI)
        self.graph_builder = graph_builder

    @override
    def read(self) -> Graph:
        """Copy the language vocabulary and drop its concepts without ISO 639-1 (but the extra ones)."""
        graph = Graph()
        graph += self.graph_builder()
        for concept in list(graph.subjects(RDF.type, SKOS.Concept)):
            notations = [
                notation for notation in graph.objects(concept, SKOS.notation) if isinstance(notation, Literal)
            ]
            if not any(
                notation.datatype == EUVOC_NAMESPACE.ISO_639_1
                or (notation.datatype == NOTATION_ID_DATATYPE and str(notation) in EXTRA_PRIMARY_LANGUAGES)
                for notation in notations
            ):
                graph.remove((concept, None, None))
                graph.remove((None, None, concept))
        return graph

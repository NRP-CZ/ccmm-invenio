#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

import yaml
from rdflib import RDF, SKOS, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import PROPS_NAMESPACE, make_vocabulary_namespace
from ccmm_invenio.fixtures.compiler.invenio_export import export_subjects
from ccmm_invenio.fixtures.compiler.readers import INSPIRE_SCHEME, InspireThemesReader

REGISTER = "http://inspire.ec.europa.eu/theme"

# the register document of a language: a valid theme (ef) and a retired one (xx),
# with the labels and definitions in that language only, and register metadata
DOCUMENT = """<?xml version='1.0' encoding='utf-8'?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#" xmlns:adms="http://www.w3.org/ns/adms#"
    xmlns:dct="http://purl.org/dc/terms/">
  <rdf:Description rdf:about="http://inspire.ec.europa.eu/theme">
    <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#ConceptScheme"/>
    <dct:created rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2013-03-25 14:14 PM UTC</dct:created>
  </rdf:Description>
  <rdf:Description rdf:about="http://inspire.ec.europa.eu/theme/ef">
    <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
    <skos:inScheme rdf:resource="http://inspire.ec.europa.eu/theme"/>
    <skos:topConceptOf rdf:resource="http://inspire.ec.europa.eu/theme"/>
    <adms:status rdf:resource="http://inspire.ec.europa.eu/registry/status/valid"/>
    <dct:hasFormat rdf:resource="http://inspire.ec.europa.eu/theme/ef/ef.{lang}.html"/>
    <skos:prefLabel xml:lang="{lang}">{ef_label}</skos:prefLabel>
    <skos:definition xml:lang="{lang}">{ef_definition}</skos:definition>
  </rdf:Description>
  <rdf:Description rdf:about="http://inspire.ec.europa.eu/theme/xx">
    <rdf:type rdf:resource="http://www.w3.org/2004/02/skos/core#Concept"/>
    <skos:inScheme rdf:resource="http://inspire.ec.europa.eu/theme"/>
    <adms:status rdf:resource="http://inspire.ec.europa.eu/registry/status/retired"/>
    <skos:prefLabel xml:lang="{lang}">Retired</skos:prefLabel>
  </rdf:Description>
</rdf:RDF>
"""

TEXTS = {
    "en": ("Environmental monitoring facilities", "Location and operation of environmental monitoring facilities."),
    "cs": ("Zařízení pro sledování životního prostředí", "Rozmístění a provoz zařízení pro sledování."),
}


def patch_register(monkeypatch, tmp_path):
    """Serve the register documents of the languages from files."""
    for lang, (label, definition) in TEXTS.items():
        (tmp_path / f"theme.{lang}.rdf").write_text(
            DOCUMENT.format(lang=lang, ef_label=label, ef_definition=definition), encoding="utf-8"
        )
    monkeypatch.setattr(InspireThemesReader, "document_url", lambda _self, lang: str(tmp_path / f"theme.{lang}.rdf"))


def test_document_url():
    assert InspireThemesReader().document_url("cs") == "http://inspire.ec.europa.eu/theme/theme.cs.rdf"


def test_inspire_themes(monkeypatch, tmp_path):
    patch_register(monkeypatch, tmp_path)
    graph = InspireThemesReader().read()
    vocab = make_vocabulary_namespace("subjects")

    # only the valid theme, re-homed under the scheme-prefixed code
    themes = set(graph.subjects(RDF.type, SKOS.Concept))
    assert themes == {vocab["inspire:ef"]}
    ef = vocab["inspire:ef"]
    assert (ef, SKOS.exactMatch, URIRef(f"{REGISTER}/ef")) in graph

    # the labels and definitions of both languages; the register metadata is not kept
    assert (ef, SKOS.prefLabel, Literal("Environmental monitoring facilities", lang="en")) in graph
    assert (ef, SKOS.prefLabel, Literal("Zařízení pro sledování životního prostředí", lang="cs")) in graph
    assert (ef, SKOS.definition, Literal(TEXTS["en"][1], lang="en")) in graph
    assert not list(graph.objects(ef, URIRef("http://purl.org/dc/terms/hasFormat")))

    # the theme code, upper case as ccmm records use it
    assert (ef, PROPS_NAMESPACE.classification_code, Literal("EF")) in graph


def test_export_inspire_themes(monkeypatch, tmp_path):
    patch_register(monkeypatch, tmp_path)
    output_path = tmp_path / "subjects_inspire.yaml"
    export_subjects(InspireThemesReader().read(), output_path, INSPIRE_SCHEME)

    assert yaml.safe_load(output_path.read_text(encoding="utf-8")) == [
        {
            "id": "inspire:ef",
            "scheme": "INSPIRE",
            "title": {"cs": "Zařízení pro sledování životního prostředí", "en": "Environmental monitoring facilities"},
            "subject": "Environmental monitoring facilities",
            "props": {"classification_code": "EF"},
            "identifiers": [{"scheme": "url", "identifier": f"{REGISTER}/ef"}],
        }
    ]

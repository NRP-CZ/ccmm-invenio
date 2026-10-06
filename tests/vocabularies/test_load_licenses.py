#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests of the licenses vocabulary and its curated CC family fragment."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest
import yaml
from rdflib import RDF, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.invenio_export import export_vocabulary
from ccmm_invenio.fixtures.compiler.readers import (
    CuratedVocabularyReader,
    LicensesMerger,
    RDMLicensesReader,
)

DATA_DIR = Path(files("ccmm_invenio.fixtures.input.vocabularies"))


def merged_licenses() -> Graph:
    """Return the RDM licenses merged with the curated CC family fragment."""
    return LicensesMerger(
        CuratedVocabularyReader(DATA_DIR / "licenses.ttl", "licenses").read(),
        RDMLicensesReader("uri:does_not_matter").read(),
    ).merge()


def test_load_licenses():
    reader = RDMLicensesReader("uri:does_not_matter")
    licenses = reader.read()

    assert isinstance(licenses, Graph)

    vocab = make_vocabulary_namespace("licenses")

    # all 419 fixture entries became concepts
    assert len(set(licenses.subjects(RDF.type, SKOS.Concept))) == 419

    # a plain entry, carrying its id notation, label, tags and props
    mit = vocab["mit"]
    assert (mit, RDF.type, SKOS.Concept) in licenses
    assert (mit, SKOS.inScheme, URIRef(vocab)) in licenses
    assert [str(n) for n in licenses.objects(mit, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["mit"]
    assert (mit, SKOS.prefLabel, Literal("MIT License", lang="en")) in licenses

    # the comma-separated csv tags become individual tag values
    assert (mit, TAGS_URI, Literal("recommended")) in licenses
    assert (mit, TAGS_URI, Literal("all")) in licenses
    assert (mit, TAGS_URI, Literal("software")) in licenses

    # the props__* columns become the props
    assert (mit, PROPS_NAMESPACE.url, Literal("https://opensource.org/license/mit")) in licenses
    assert (mit, PROPS_NAMESPACE.scheme, Literal("spdx")) in licenses
    assert (mit, PROPS_NAMESPACE.osi_approved, Literal("y")) in licenses

    # the concept is matched to the license its URL points to
    assert (mit, SKOS.exactMatch, URIRef("https://opensource.org/license/mit")) in licenses
    assert (
        vocab["cc-by-4.0"],
        SKOS.exactMatch,
        URIRef("https://creativecommons.org/licenses/by/4.0/"),
    ) in licenses

    # an entry with a description and an empty prop (osi_approved)
    cc_by = vocab["cc-by-4.0"]
    assert (
        cc_by,
        SKOS.definition,
        Literal(
            "The Creative Commons Attribution license allows re-distribution "
            "and re-use of a licensed work on the condition that the creator "
            "is appropriately credited.",
            lang="en",
        ),
    ) in licenses
    assert (cc_by, PROPS_NAMESPACE.osi_approved, None) not in licenses

    # the vocabulary is flat: every entry is a top concept
    concepts = set(licenses.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(licenses.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(licenses.triples((None, SKOS.broader, None)))


def test_cc_family_fragment():
    """The curated fragment grows the CC family tree on the RDM licenses."""
    graph = merged_licenses()
    vocab = make_vocabulary_namespace("licenses")

    # the 419 RDM licenses plus the six introduced tree nodes
    assert len(set(graph.subjects(RDF.type, SKOS.Concept))) == 419 + 6

    # an introduced tree node: a concept with its id notation and labels
    cc_4_0 = vocab["cc-4.0"]
    assert (cc_4_0, RDF.type, SKOS.Concept) in graph
    assert (cc_4_0, SKOS.inScheme, URIRef(vocab)) in graph
    assert (cc_4_0, SKOS.notation, Literal("cc-4.0", datatype=NOTATION_ID_DATATYPE)) in graph
    assert (cc_4_0, SKOS.prefLabel, Literal("verze 4.0 mezinárodní licence", lang="cs")) in graph
    assert (cc_4_0, SKOS.prefLabel, Literal("version 4.0 International License", lang="en")) in graph

    # the hierarchy: cc -> version -> license, cc0 under cc
    assert (cc_4_0, SKOS.broader, vocab["cc"]) in graph
    cc_by = vocab["cc-by-4.0"]
    assert (cc_by, SKOS.broader, cc_4_0) in graph
    assert (vocab["cc0-1.0"], SKOS.broader, vocab["cc"]) in graph

    # the Czech labels and descriptions of the RDM licenses, their English
    # ones kept from the fixture
    assert (
        cc_by,
        SKOS.prefLabel,
        Literal("Creative Commons Uveďte původ 4.0 Mezinárodní licence", lang="cs"),
    ) in graph
    assert (
        cc_by,
        SKOS.prefLabel,
        Literal("Creative Commons Attribution 4.0 International", lang="en"),
    ) in graph
    assert (
        cc_by,
        SKOS.definition,
        Literal(
            "Umožňuje ostatním rozmnožovat, rozšiřovat, vystavovat a "
            "sdělovat dílo a z něj odvozená díla pouze při uvedení autora. "
            "V češtině: Uveďte původ (v češtině dříve označováno jako "
            "Uveďte autora); v angličtině: Attribution; zkratka CC BY.",
            lang="cs",
        ),
    ) in graph

    # only the international licenses are in the family: the jurisdiction
    # ports stay flat and keep no Czech labels
    for port in ("cc-by-3.0-at", "cc-by-3.0-us", "cc-by-sa-2.0-uk", "cc-by-nc-nd-3.0-igo"):
        assert (vocab[port], SKOS.broader, None) not in graph
        assert all(label.language != "cs" for label in graph.objects(vocab[port], SKOS.prefLabel))

    # the top-concept structure follows the hierarchy: cc is a top concept,
    # the versions and the licenses below them are not - and the licenses
    # outside the family still are
    scheme = URIRef(vocab)
    assert (vocab["cc"], SKOS.topConceptOf, scheme) in graph
    assert (scheme, SKOS.hasTopConcept, vocab["cc"]) in graph
    assert (cc_4_0, SKOS.topConceptOf, None) not in graph
    assert (cc_by, SKOS.topConceptOf, None) not in graph
    assert (vocab["mit"], SKOS.topConceptOf, scheme) in graph


def test_cc_family_fragment_export(tmp_path):
    """The exported fixture carries the hierarchy and the Czech labels."""
    export_vocabulary(merged_licenses(), tmp_path / "licenses.yaml")
    entries = yaml.safe_load((tmp_path / "licenses.yaml").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in entries}

    assert by_id["cc"]["title"] == {
        "cs": "Licence Creative Commons",
        "en": "License Creative Commons",
    }
    assert by_id["cc-4.0"]["hierarchy"] == {"parent": "cc"}
    assert by_id["cc-by-4.0"]["hierarchy"] == {"parent": "cc-4.0"}
    assert by_id["cc-by-4.0"]["title"]["cs"] == ("Creative Commons Uveďte původ 4.0 Mezinárodní licence")
    # the RDM data of the enriched licenses survives
    assert by_id["cc-by-4.0"]["props"]["url"] == "https://creativecommons.org/licenses/by/4.0/"
    # the ports stay flat
    assert "hierarchy" not in by_id["cc-by-3.0-at"]

    # the parents precede their children, so that the loader can load them
    order = [entry["id"] for entry in entries]
    assert order.index("cc") < order.index("cc-1.0") < order.index("cc-by-1.0")


def test_cc_family_fragment_stale_subject(tmp_path):
    """An untyped subject that is no RDM license fails the merge."""
    fragment = tmp_path / "fragment.ttl"
    fragment.write_text(
        "@prefix licenses: <https://nma.eosc.cz/vocabularies/licenses/> .\n"
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        "\n"
        'licenses:no-such-license skos:prefLabel "Žádná taková licence"@cs .\n',
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match="not a concept of the target"):
        LicensesMerger(
            CuratedVocabularyReader(fragment, "licenses").read(),
            RDMLicensesReader("uri:does_not_matter").read(),
        ).merge()


def test_cc_family_fragment_introduces_stale_concept(tmp_path):
    """A typed subject is created even when the vocabulary does not know it."""
    fragment = tmp_path / "fragment.ttl"
    fragment.write_text(
        "@prefix invenio: <https://nma.eosc.cz/vocabularies/vocabularies/invenio> .\n"
        "@prefix licenses: <https://nma.eosc.cz/vocabularies/licenses/> .\n"
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        "\n"
        "licenses:cc-new a skos:Concept ;\n"
        "    skos:inScheme licenses: ;\n"
        '    skos:notation "cc-new"^^invenio:id ;\n'
        '    skos:prefLabel "nová verze"@cs , "new version"@en .\n',
        encoding="utf-8",
    )

    graph = LicensesMerger(
        CuratedVocabularyReader(fragment, "licenses").read(),
        RDMLicensesReader("uri:does_not_matter").read(),
    ).merge()

    vocab = make_vocabulary_namespace("licenses")
    assert (vocab["cc-new"], RDF.type, SKOS.Concept) in graph
    # an introduced concept without a parent becomes a top concept
    assert (vocab["cc-new"], SKOS.topConceptOf, URIRef(vocab)) in graph


def test_curated_fragment_rejects_foreign_predicate(tmp_path):
    """A predicate outside the fragment shapes fails the read."""
    fragment = tmp_path / "fragment.ttl"
    fragment.write_text(
        "@prefix licenses: <https://nma.eosc.cz/vocabularies/licenses/> .\n"
        "\n"
        'licenses:cc-by-4.0 <http://example.org/props/not-a-prop> "nope" .\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not a predicate of the fragment"):
        CuratedVocabularyReader(fragment, "licenses").read()


def test_curated_fragment_rejects_plain_label(tmp_path):
    """A label without a language tag fails the read."""
    fragment = tmp_path / "fragment.ttl"
    fragment.write_text(
        "@prefix licenses: <https://nma.eosc.cz/vocabularies/licenses/> .\n"
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        "\n"
        'licenses:cc-by-4.0 skos:prefLabel "Creative Commons Uveďte původ" .\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not a language-tagged literal"):
        CuratedVocabularyReader(fragment, "licenses").read()


def test_curated_fragment_rejects_concept_without_id(tmp_path):
    """A typed subject without its id notation fails the read."""
    fragment = tmp_path / "fragment.ttl"
    fragment.write_text(
        "@prefix licenses: <https://nma.eosc.cz/vocabularies/licenses/> .\n"
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        "\n"
        "licenses:cc-new a skos:Concept ;\n"
        "    skos:inScheme licenses: ;\n"
        '    skos:prefLabel "nová verze"@cs .\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="no id notation"):
        CuratedVocabularyReader(fragment, "licenses").read()

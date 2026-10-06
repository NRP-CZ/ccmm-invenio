#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from rdflib import RDF, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    NOTATION_ID_DATATYPE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import COARAccessRightsReader

COAR = "http://purl.org/coar/access_right/"
SCHEME = COAR + "scheme"

OPEN_ACCESS_DEFINITION = (
    "Open access refers to a resource that is immediately and permanently "
    "online, and free for all on the Web, without financial and technical "
    "barriers.The resource is either stored in the repository or referenced "
    "to an external journal or trustworthy archive."
)


def make_coar_source_graph():
    """Return a mocked COAR access rights vocabulary with its four concepts."""
    source = Graph()
    source.add((URIRef(SCHEME), RDF.type, SKOS.ConceptScheme))
    source.add((URIRef(SCHEME), SKOS.hasTopConcept, URIRef(COAR + "c_abf2")))
    source.add((URIRef(SCHEME), SKOS.hasTopConcept, URIRef(COAR + "c_f1cf")))
    source.add((URIRef(SCHEME), SKOS.hasTopConcept, URIRef(COAR + "c_16ec")))
    source.add((URIRef(SCHEME), SKOS.hasTopConcept, URIRef(COAR + "c_14cb")))

    # open access
    open_access = URIRef(COAR + "c_abf2")
    source.add((open_access, RDF.type, SKOS.Concept))
    source.add((open_access, SKOS.inScheme, URIRef(SCHEME)))
    source.add((open_access, SKOS.topConceptOf, URIRef(SCHEME)))
    source.add((open_access, SKOS.prefLabel, Literal("open access", lang="en")))
    source.add((open_access, SKOS.prefLabel, Literal("otevřený přístup", lang="cs")))
    source.add((open_access, SKOS.prefLabel, Literal("オープンアクセス", lang="ja")))
    source.add((open_access, SKOS.altLabel, Literal("open access", lang="fr")))
    source.add((open_access, SKOS.definition, Literal(OPEN_ACCESS_DEFINITION, lang="en")))
    source.add((open_access, SKOS.relatedMatch, URIRef("http://purl.org/eprint/accessRights/OpenAccess")))
    source.add(
        (
            open_access,
            SKOS.relatedMatch,
            URIRef("https://vocabs.acdh.oeaw.ac.at/archeaccessrestrictions/public"),
        )
    )
    source.add((open_access, SKOS.editorialNote, Literal("Published", lang="en")))

    # embargoed, restricted and metadata only access, in brief
    for code, en, cs in (
        ("c_f1cf", "embargoed access", "odložené zpřístupnění"),
        ("c_16ec", "restricted access", "omezený přístup"),
        ("c_14cb", "metadata only access", "pouze metadata"),
    ):
        concept = URIRef(COAR + code)
        source.add((concept, RDF.type, SKOS.Concept))
        source.add((concept, SKOS.inScheme, URIRef(SCHEME)))
        source.add((concept, SKOS.topConceptOf, URIRef(SCHEME)))
        source.add((concept, SKOS.prefLabel, Literal(en, lang="en")))
        source.add((concept, SKOS.prefLabel, Literal(cs, lang="cs")))
    return source


def test_coar_access_rights(monkeypatch):
    monkeypatch.setattr(COARAccessRightsReader, "fetch_source", lambda _self: make_coar_source_graph())

    reader = COARAccessRightsReader()
    graph = reader.read()

    vocab = make_vocabulary_namespace("accessrights")

    # the COAR codes are re-homed under the InvenioRDM access statuses
    open_access = vocab["open"]
    assert (open_access, RDF.type, SKOS.Concept) in graph
    assert (open_access, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(open_access, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["open"]

    # linked to the COAR authority, labels kept with their languages - in
    # the supported label languages only
    assert (open_access, SKOS.exactMatch, URIRef(COAR + "c_abf2")) in graph
    assert (open_access, SKOS.prefLabel, Literal("open access", lang="en")) in graph
    assert (open_access, SKOS.prefLabel, Literal("otevřený přístup", lang="cs")) in graph
    assert (open_access, SKOS.prefLabel, Literal("オープンアクセス", lang="ja")) not in graph

    # definitions, altLabels and relatedMatch links are kept - the labels
    # again in the supported languages only
    assert (open_access, SKOS.definition, Literal(OPEN_ACCESS_DEFINITION, lang="en")) in graph
    assert (open_access, SKOS.altLabel, Literal("open access", lang="fr")) not in graph
    assert (
        open_access,
        SKOS.relatedMatch,
        URIRef("http://purl.org/eprint/accessRights/OpenAccess"),
    ) in graph

    # the vocabulary is flat: every entry is a top concept
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(graph.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(graph.triples((None, SKOS.broader, None)))
    assert {str(c).rsplit("/", 1)[-1] for c in concepts} == {
        "open",
        "embargoed",
        "restricted",
        "metadata-only",
    }

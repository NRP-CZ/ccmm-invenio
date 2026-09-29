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
    TAGS_URI,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import RDMRemovalReasonsReader


def test_load_removal_reasons():
    reader = RDMRemovalReasonsReader("uri:does_not_matter")
    removal_reasons = reader.read()

    assert isinstance(removal_reasons, Graph)

    vocab = make_vocabulary_namespace("removalreasons")

    # a tagged concept, carrying its id notation and labels
    duplicate = vocab["duplicate"]
    assert (duplicate, RDF.type, SKOS.Concept) in removal_reasons
    assert (duplicate, SKOS.inScheme, URIRef(vocab)) in removal_reasons
    assert [
        str(n) for n in removal_reasons.objects(duplicate, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE
    ] == ["duplicate"]
    assert (duplicate, SKOS.prefLabel, Literal("Duplicate of another record", lang="en")) in removal_reasons
    assert (duplicate, SKOS.prefLabel, Literal("Duplikát jiného záznamu", lang="cs")) in removal_reasons
    assert (duplicate, TAGS_URI, Literal("deletion-request")) in removal_reasons

    # the vocabulary is flat: every entry is a top concept
    concepts = set(removal_reasons.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(removal_reasons.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(removal_reasons.triples((None, SKOS.broader, None)))

    # an untagged concept carries no tag triples
    spam = vocab["spam"]
    assert not list(removal_reasons.objects(spam, TAGS_URI))

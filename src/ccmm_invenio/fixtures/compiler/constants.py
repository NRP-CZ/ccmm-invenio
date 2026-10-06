#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Constants of the vocabulary conversion."""

from __future__ import annotations

from rdflib import RDF, SKOS, Namespace, URIRef

SUPPORTED_LABEL_LANGUAGES = frozenset({"cs", "en"})
"""The only language codes labels and descriptions are read in.

The readers keep the prefLabels, altLabels and definitions of the source
concepts in these languages only and discard the ones in any other code -
the vocabularies serve the Czech and English UIs, and the other languages
would bloat the fixtures (the EU file types alone are labelled in all the
EU languages, the ISO 639-3 languages in ~70 of them).
"""

NMA_NAMESPACE = Namespace("https://nma.eosc.cz/vocabularies/")
"""NMA vocabulary namespace."""

VOCAB_NAMESPACE = Namespace("https://nma.eosc.cz/vocabularies/vocabularies/invenio")
"""Parent namespace of the internal vocabulary constructs: the props, the
tags and the id-notation datatype live below it (see :data:`PROPS_NAMESPACE`,
:data:`TAGS_URI`, :data:`NOTATION_ID_DATATYPE`)."""

PROPS_NAMESPACE = Namespace(VOCAB_NAMESPACE.props)
"""NMA vocabulary properties namespace."""

TAGS_URI = VOCAB_NAMESPACE.tags
"""NMA vocabulary tags namespace."""

NOTATION_ID_DATATYPE = VOCAB_NAMESPACE.id
"""Datatype marking a skos:notation as our internal vocabulary id.

A skos:notation literal's datatype identifies its notation scheme, which is
how our notations can be told apart from any foreign ones in a merged graph.
"""

EUROPA_LANGUAGE_NAMESPACE = Namespace("http://publications.europa.eu/resource/authority/language/")
"""EU Publications Office language authority; identifiers are ISO 639-3 codes."""

EUVOC_NAMESPACE = Namespace("http://publications.europa.eu/ontology/euvoc#")
"""EU Vocabularies ontology (euvoc); defines the notation datatypes for
language code schemes (e.g. ISO_639_1, ISO_639_3, XML_LNG)."""

DCE_NAMESPACE = Namespace("http://purl.org/dc/elements/1.1/")
"""Dublin Core elements namespace; used by the EU authority tables."""

COAR_RESOURCE_TYPE_NAMESPACE = Namespace("http://purl.org/coar/resource_type/")
"""COAR resource types vocabulary; identifiers are the COAR concept codes
(e.g. ``c_2f33``, ``C53B-JCY5``)."""

DATACITE_RESOURCE_TYPE_NAMESPACE = Namespace("https://w3id.org/tib/datacite/vocab/resourceTypeGeneral/")
"""TIB DataCite resourceTypeGeneral vocabulary; identifiers are the
camelCase resourceTypeGeneral names (e.g. Text, BookChapter)."""

DATACITE_TITLE_TYPE_NAMESPACE = Namespace("https://w3id.org/tib/datacite/vocab/titleType/")
"""TIB DataCite titleType vocabulary; identifiers are the camelCase titleType
names (e.g. AlternativeTitle, Subtitle)."""

DATACITE_DESCRIPTION_TYPE_NAMESPACE = Namespace("https://w3id.org/tib/datacite/vocab/descriptionType/")
"""TIB DataCite descriptionType vocabulary; identifiers are the camelCase
descriptionType names (e.g. SeriesInformation, TechnicalInfo)."""

DATACITE_DATE_TYPE_NAMESPACE = Namespace("https://w3id.org/tib/datacite/vocab/dateType/")
"""TIB DataCite dateType vocabulary; identifiers are the camelCase dateType
names (e.g. Collected, Copyrighted)."""

DATACITE_CONTRIBUTOR_TYPE_NAMESPACE = Namespace("https://w3id.org/tib/datacite/vocab/contributorType/")
"""TIB DataCite contributorType vocabulary; identifiers are the camelCase
contributorType names (e.g. ContactPerson, WorkPackageLeader)."""

IANA_MEDIA_TYPE_NAMESPACE = Namespace("http://www.iana.org/assignments/media-types/")
"""IANA media types registry; the media type is the IRI path
(e.g. ``.../media-types/application/pdf``). CCMM points at these IRIs in
their http form."""

REBUILT_PREDICATES = (RDF.type, SKOS.inScheme, SKOS.topConceptOf, SKOS.notation)
"""Predicates the vocabulary readers rebuild themselves when re-homing
concepts (concept type, scheme membership, the id notation) - everything
else is copied over from the source concepts."""

HIERARCHY_REBUILT_PREDICATES = (*REBUILT_PREDICATES, SKOS.broader, SKOS.narrower)
"""Like :data:`REBUILT_PREDICATES`, plus the hierarchy links - for readers
that re-target the source's ``skos:broader``/``skos:narrower`` between the
re-homed concepts instead of copying them as-is."""

SKOS_MAPPING_PROPERTIES: dict[str, URIRef] = {
    "exactMatch": SKOS.exactMatch,
    "closeMatch": SKOS.closeMatch,
    "broadMatch": SKOS.broadMatch,
    "narrowMatch": SKOS.narrowMatch,
    "relatedMatch": SKOS.relatedMatch,
}
"""The SKOS mapping properties, by their local names.

These are the links the vocabulary concepts carry to their counterparts in
other vocabularies: the SSSOM mapping sets merged in on the way to the
fixtures speak them (see
:class:`~ccmm_invenio.fixtures.compiler.readers.sssom.SSSOMMappingsReader`),
and so do the oarepo-vocabularies mappings of the fixture entries on the
way out (see
:mod:`~ccmm_invenio.fixtures.compiler.invenio_export`). Keeping both
sides on this one table makes sure they stay in step.
"""

MISSING_EUROPA_LANGUAGE_CODES = frozenset({"isv", "izm", "rsw", "zyg"})
"""ISO 639-3 codes with no counterpart in the EU language authority table.

Verified against its 20260617-0 release - the four are recent ISO additions
the authority has not taken over yet, so the languages carry no
``skos:exactMatch`` link for them.
"""


def make_vocabulary_namespace(vocab_type: str) -> Namespace:
    """Create a NMA vocabulary namespace from the given type.

    Terms are then created with ``namespace[term]``, e.g. ``languages["CES"]``.
    """
    return Namespace(NMA_NAMESPACE + vocab_type + "/")

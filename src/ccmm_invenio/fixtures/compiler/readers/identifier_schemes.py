#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Reader for the identifier scheme configs of invenio_rdm_records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, override

# idutils re-exports its members only at import time (see its
# import_attributes), so the constant is imported from its defining module
from idutils.normalizers import IDUTILS_LANDING_URLS
from rdflib import SKOS, Graph, Literal, URIRef

from ..constants import (
    PROPS_NAMESPACE,
    TAGS_URI,
    make_vocabulary_namespace,
)
from ..declarations import semantic_declarations
from ..merger import CuratedVocabularyMerger
from .base import NO_SOURCE_URI, VocabularyReader

if TYPE_CHECKING:
    from collections.abc import Mapping

PERSON_ORGANIZATION_TAG = "person-organization"
"""Tag of the schemes usable as identifiers of persons and organizations."""

RECORD_TAG = "record"
"""Tag of the schemes usable as (alternate, related, reference) identifiers
of records."""


class RDMIdentifierSchemesReader(VocabularyReader):
    """A reader for the identifier schemes of invenio_rdm_records.

    InvenioRDM does not ship an identifier schemes vocabulary fixture - the
    schemes live as config dictionaries (see :meth:`schemes`):
    ``RDM_RECORDS_PERSONORG_SCHEMES`` lists the schemes of creator,
    contributor and organization identifiers, ``RDM_RECORDS_IDENTIFIERS_
    SCHEMES`` the ones of record (main, alternate, related and reference)
    identifiers. Their union is read here; each entry becomes a
    ``skos:Concept`` under the NMA identifierschemes namespace, tagged
    by the configs it came from, with the config label as the prefLabel and
    the DataCite identifier name under the ``datacite`` prop.

    CCMM represents schemes by their resolver IRIs (e.g.
    ``https://orcid.org/``, ``https://doi.org/``); where idutils knows the
    landing URL template of a scheme, its ``{pid}``-stripped prefix is that
    resolver IRI and is linked via ``skos:exactMatch``. The schemes
    without a landing URL template (e.g. ``isni``, ``grid``) carry no
    exact match.

    In contrast to the fixture readers, reading this vocabulary requires
    importing the ``invenio_rdm_records`` config - it is loaded lazily in
    :meth:`schemes` to keep importing the readers cheap.
    """

    vocabulary_type: ClassVar[str] = "identifierschemes"

    def __init__(self, uri: str = NO_SOURCE_URI):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

    @override
    def read(self) -> Graph:
        """Build the identifier schemes vocabulary graph from the configs."""
        graph = Graph()
        graph += semantic_declarations()
        vocabulary = make_vocabulary_namespace(self.vocabulary_type)

        for scheme, tags in sorted(self.schemes().items()):
            entry = self.entry(scheme)
            concept_uri = self.add_concept(graph, vocabulary, scheme)

            # the config labels are lazy translations; their default is English
            graph.add((concept_uri, SKOS.prefLabel, Literal(str(entry["label"]), lang="en")))

            # the DataCite identifier name of the scheme (e.g. ORCID, arXiv)
            if datacite := entry.get("datacite"):
                graph.add((concept_uri, PROPS_NAMESPACE.datacite, Literal(str(datacite))))

            # which of the config dictionaries the scheme comes from - the
            # person/organization ones are the identifiers of agents, the
            # record ones of resources
            for tag in tags:
                graph.add((concept_uri, TAGS_URI, Literal(tag)))

            # the resolver IRI is what CCMM points its scheme IRIs at
            if scheme_iri := self.scheme_iri(scheme):
                graph.add((concept_uri, SKOS.exactMatch, URIRef(scheme_iri)))
        return graph

    def configs(self) -> tuple[tuple[str, Mapping[str, Mapping[str, Any]]], ...]:
        """Return the (tag, config dict) pairs the schemes are read from.

        The single point where the ``invenio_rdm_records`` config pair is
        named and lazily imported - :meth:`schemes` and :meth:`entry` both
        derive from it, so a third config only needs adding here.
        """
        from invenio_rdm_records import config

        return (
            (PERSON_ORGANIZATION_TAG, config.RDM_RECORDS_PERSONORG_SCHEMES),
            (RECORD_TAG, config.RDM_RECORDS_IDENTIFIERS_SCHEMES),
        )

    def schemes(self) -> dict[str, tuple[str, ...]]:
        """Collect the identifier schemes of the config dictionaries.

        Returns a mapping of the scheme keys to the tags of the configs
        they appear in; schemes of both configs carry both tags.
        """
        schemes: dict[str, tuple[str, ...]] = {}
        for tag, config_schemes in self.configs():
            for scheme in config_schemes:
                tags = schemes.setdefault(scheme, ())
                schemes[scheme] = (*tags, tag)
        return schemes

    def entry(self, scheme: str) -> Mapping[str, Any]:
        """Return the config entry the given scheme key is described by.

        The person/organization config takes precedence: its entry carries
        the DataCite name InvenioRDM validates agent identifiers against.
        """
        for _tag, config_schemes in self.configs():
            if scheme in config_schemes:
                entry: Mapping[str, Any] = config_schemes[scheme]
                return entry
        raise KeyError(scheme)

    def scheme_iri(self, scheme: str) -> str | None:
        """Return the resolver IRI of the given scheme key, if known.

        The landing URL templates of idutils resolve an identifier value
        into a URL by appending it to the template; the template without
        its ``{pid}`` placeholder is thus the resolver namespace the scheme
        is identified by in CCMM (e.g. ``https://orcid.org/``). Templates
        not ending in the placeholder (none of the current ones do) and
        schemes without a template yield ``None``.
        """
        template: str | None = IDUTILS_LANDING_URLS.get(scheme)
        if template is None or not template.endswith("{pid}"):
            return None
        return template.removesuffix("{pid}").replace("{scheme}", "https")


class IdentifiersMerger(CuratedVocabularyMerger):
    """Merge the curated identifier schemes into the RDM identifier schemes.

    Both the fragment (see
    :class:`~.curated.CuratedVocabularyReader`) and the configs emit their
    concepts into the same NMA identifierschemes namespace, so the concepts
    are matched by URI: the concepts the fragment introduces (the schemes
    the RDM configs do not carry - ares, iri, researcherid, scopusid) are
    created in the vocabulary with their labels, tags and authority links.
    An untyped subject of the fragment that is not a concept of the
    vocabulary fails the merge - the fragment has gone stale.
    """

    vocabulary_type: ClassVar[str] = "identifierschemes"

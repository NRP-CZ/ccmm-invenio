#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""The prefixes bound before the turtle export of the vocabularies."""

from __future__ import annotations

from rdflib import DCTERMS, OWL, RDF, RDFS, SKOS

from .constants import (
    DCE_NAMESPACE,
    EUVOC_NAMESPACE,
    NMA_NAMESPACE,
    PROPS_NAMESPACE,
    TAGS_URI,
)

TURTLE_PREFIXES = {
    # the well-known ontologies
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "skos": SKOS,
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "prov": "http://www.w3.org/ns/prov#",
    "schema": "https://schema.org/",
    "dcterms": DCTERMS,
    "dce": DCE_NAMESPACE,
    "euvoc": EUVOC_NAMESPACE,
    "dcmitype": "http://purl.org/dc/dcmitype/",
    "bibo": "http://purl.org/ontology/bibo/",
    "fabio": "http://purl.org/spar/fabio/",
    "efo": "http://www.ebi.ac.uk/efo/",
    "mesh": "http://purl.bioontology.org/ontology/MESH/",
    "snomedct": "http://purl.bioontology.org/ontology/SNOMEDCT/",
    "ncit": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#",
    "odo": "http://purl.dataone.org/odo/",
    "purljp": "http://purl.jp/bio/4/id/",
    "elter": "http://vocabs.lter-europe.net/elter_cl/",
    "elter-page": "https://vocabs.lter-europe.net/elter_cl/en/page/",
    "loc-contenttypes": "http://id.loc.gov/vocabulary/contentTypes/",
    "loc-resourcetypes": "https://id.loc.gov/vocabulary/resourceTypes/",
    "arche-access-restrictions": "https://vocabs.acdh.oeaw.ac.at/archeaccessrestrictions/",
    "arche-category": "https://vocabs.acdh.oeaw.ac.at/archecategory/model/",
    "fabio-docs": "https://sparontologies.github.io/fabio/current/fabio.html#",
    "coar-access-right": "http://purl.org/coar/access_right/",
    "coar-resource-type": "http://purl.org/coar/resource_type/",
    "eprint-access-rights": "http://purl.org/eprint/accessRights/",
    "eprint-type": "http://purl.org/eprint/type/",
    # the TIB DataCite vocabularies and schema
    "datacite-contributortype": "https://w3id.org/tib/datacite/vocab/contributorType/",
    "datacite-datetype": "https://w3id.org/tib/datacite/vocab/dateType/",
    "datacite-descriptiontype": "https://w3id.org/tib/datacite/vocab/descriptionType/",
    "datacite-relationtype": "https://w3id.org/tib/datacite/vocab/relationType/",
    "datacite-resourcetypegeneral": "https://w3id.org/tib/datacite/vocab/resourceTypeGeneral/",
    "datacite-titletype": "https://w3id.org/tib/datacite/vocab/titleType/",
    "datacite-v4.4": "http://purl.org/datacite/v4.4/",
    "datacite-metadata-schema": "https://datacite-metadata-schema.readthedocs.io/en/4.5/appendices/appendix-1/resourceTypeGeneral/#",
    # the CCMM codelists
    "ccmm-agentrole": "https://vocabs.ccmm.cz/registry/codelist/AgentRole/",
    "ccmm-agentrole-contributor": "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Contributor/",
    "ccmm-alternatetitle": "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/",
    "ccmm-descriptiontype": "https://vocabs.ccmm.cz/registry/codelist/DescriptionType/",
    "ccmm-locationrelation": "https://vocabs.ccmm.cz/registry/codelist/LocationRelation/",
    "ccmm-relationtype": "https://vocabs.ccmm.cz/registry/codelist/RelationType/",
    "ccmm-timereference": "https://vocabs.ccmm.cz/registry/codelist/TimeReference/",
    # the NMA vocabularies
    "nma": NMA_NAMESPACE,
    "props": PROPS_NAMESPACE,
    "tags": TAGS_URI,
    "nma-accessrights": "https://nma.eosc.cz/vocabularies/accessrights/",
    "nma-checksumalgorithms": "https://nma.eosc.cz/vocabularies/checksumalgorithms/",
    "nma-datetypes": "https://nma.eosc.cz/vocabularies/datetypes/",
    "nma-descriptiontypes": "https://nma.eosc.cz/vocabularies/descriptiontypes/",
    "nma-fileformats": "https://nma.eosc.cz/vocabularies/fileformats/",
    "nma-identifierschemes": "https://nma.eosc.cz/vocabularies/identifierschemes/",
    "nma-languages": "https://nma.eosc.cz/vocabularies/languages/",
    "nma-licenses": "https://nma.eosc.cz/vocabularies/licenses/",
    "nma-locationrelations": "https://nma.eosc.cz/vocabularies/locationrelations/",
    "nma-mediatypes": "https://nma.eosc.cz/vocabularies/mediatypes/",
    "nma-mediatypes-application": "https://nma.eosc.cz/vocabularies/mediatypes/application/",
    "nma-mediatypes-audio": "https://nma.eosc.cz/vocabularies/mediatypes/audio/",
    "nma-mediatypes-font": "https://nma.eosc.cz/vocabularies/mediatypes/font/",
    "nma-mediatypes-image": "https://nma.eosc.cz/vocabularies/mediatypes/image/",
    "nma-mediatypes-message": "https://nma.eosc.cz/vocabularies/mediatypes/message/",
    "nma-mediatypes-model": "https://nma.eosc.cz/vocabularies/mediatypes/model/",
    "nma-mediatypes-multipart": "https://nma.eosc.cz/vocabularies/mediatypes/multipart/",
    "nma-mediatypes-text": "https://nma.eosc.cz/vocabularies/mediatypes/text/",
    "nma-mediatypes-video": "https://nma.eosc.cz/vocabularies/mediatypes/video/",
    "nma-relationtypes": "https://nma.eosc.cz/vocabularies/relationtypes/",
    "nma-removalreasons": "https://nma.eosc.cz/vocabularies/removalreasons/",
    "nma-resourcetypes": "https://nma.eosc.cz/vocabularies/resourcetypes/",
    "nma-roles": "https://nma.eosc.cz/vocabularies/roles/",
    "nma-titletypes": "https://nma.eosc.cz/vocabularies/titletypes/",
    "nma-vocabularies": "https://nma.eosc.cz/vocabularies/vocabularies/",
    # the EU Publications Office
    "europa-ontology": "http://publications.europa.eu/ontology/",
    "europa-ontology-authority": "http://publications.europa.eu/ontology/authority/",
    "europa-authority": "http://publications.europa.eu/resource/authority/",
    "europa-language": "http://publications.europa.eu/resource/authority/language/",
    "europa-file-type": "http://publications.europa.eu/resource/authority/file-type/",
    "europa-web": "https://op.europa.eu/en/web/",
    # the IANA media type registries
    "iana-media-types": "http://www.iana.org/assignments/media-types/",
    "iana-application": "http://www.iana.org/assignments/media-types/application/",
    "iana-audio": "http://www.iana.org/assignments/media-types/audio/",
    "iana-font": "http://www.iana.org/assignments/media-types/font/",
    "iana-image": "http://www.iana.org/assignments/media-types/image/",
    "iana-message": "http://www.iana.org/assignments/media-types/message/",
    "iana-model": "http://www.iana.org/assignments/media-types/model/",
    "iana-multipart": "http://www.iana.org/assignments/media-types/multipart/",
    "iana-text": "http://www.iana.org/assignments/media-types/text/",
    "iana-video": "http://www.iana.org/assignments/media-types/video/",
    # the identifier schemes
    "ares": "https://ares.gov.cz/",
    "arxiv": "https://arxiv.org/abs/",
    "gnd": "https://d-nb.info/gnd/",
    "doi": "https://doi.org/",
    "hdl": "https://hdl.handle.net/",
    "nbn": "https://nbn-resolving.org/",
    "orcid": "https://orcid.org/",
    "ror": "https://ror.org/",
    "scicrunch": "https://scicrunch.org/resolver/",
    "adsabs": "https://ui.adsabs.harvard.edu/#abs/",
    "scopus": "https://www.scopus.com/",
    "webofscience": "https://www.webofscience.com/",
    "wikidata": "https://www.wikidata.org/entity/",
    # the license registries
    "spdx": "http://spdx.org/rdf/terms#",
    "spdx-licenses": "https://spdx.org/licenses/",
    "opensource": "https://opensource.org/license/",
    # the Creative Commons licenses
    "cc-by-1.0": "https://creativecommons.org/licenses/by/1.0/",
    "cc-by-2.0": "https://creativecommons.org/licenses/by/2.0/",
    "cc-by-2.5": "https://creativecommons.org/licenses/by/2.5/",
    "cc-by-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "cc-by-3.0-at": "https://creativecommons.org/licenses/by/3.0/at/",
    "cc-by-3.0-us": "https://creativecommons.org/licenses/by/3.0/us/",
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-nc-1.0": "https://creativecommons.org/licenses/by-nc/1.0/",
    "cc-by-nc-2.0": "https://creativecommons.org/licenses/by-nc/2.0/",
    "cc-by-nc-2.5": "https://creativecommons.org/licenses/by-nc/2.5/",
    "cc-by-nc-3.0": "https://creativecommons.org/licenses/by-nc/3.0/",
    "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-nd-2.0": "https://creativecommons.org/licenses/by-nc-nd/2.0/",
    "cc-by-nc-nd-2.5": "https://creativecommons.org/licenses/by-nc-nd/2.5/",
    "cc-by-nc-nd-3.0": "https://creativecommons.org/licenses/by-nc-nd/3.0/",
    "cc-by-nc-nd-3.0-igo": "https://creativecommons.org/licenses/by-nc-nd/3.0/igo/",
    "cc-by-nc-nd-4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "cc-by-nc-sa-1.0": "https://creativecommons.org/licenses/by-nc-sa/1.0/",
    "cc-by-nc-sa-2.0": "https://creativecommons.org/licenses/by-nc-sa/2.0/",
    "cc-by-nc-sa-2.5": "https://creativecommons.org/licenses/by-nc-sa/2.5/",
    "cc-by-nc-sa-3.0": "https://creativecommons.org/licenses/by-nc-sa/3.0/",
    "cc-by-nc-sa-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc-by-nd-1.0": "https://creativecommons.org/licenses/by-nd/1.0/",
    "cc-by-nd-2.0": "https://creativecommons.org/licenses/by-nd/2.0/",
    "cc-by-nd-2.5": "https://creativecommons.org/licenses/by-nd/2.5/",
    "cc-by-nd-3.0": "https://creativecommons.org/licenses/by-nd/3.0/",
    "cc-by-nd-4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
    "cc-by-nd-nc-1.0": "https://creativecommons.org/licenses/by-nd-nc/1.0/",
    "cc-by-sa-1.0": "https://creativecommons.org/licenses/by-sa/1.0/",
    "cc-by-sa-2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "cc-by-sa-2.0-uk": "https://creativecommons.org/licenses/by-sa/2.0/uk/",
    "cc-by-sa-2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
    "cc-by-sa-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "cc-by-sa-3.0-at": "https://creativecommons.org/licenses/by-sa/3.0/at/",
    "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-publicdomain": "https://creativecommons.org/licenses/publicdomain/",
    "cc-publicdomain-mark-1.0": "https://creativecommons.org/publicdomain/mark/1.0/",
    "cc-publicdomain-zero-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
}
"""The prefixes bound before the turtle export (see :func:`export_turtle`).

The well-known namespaces are bound to their conventional prefixes, the
namespaces of the vocabulary sources to stable readable ones: rdflib invents
the ``ns1``, ``ns2``, ... prefixes of unbound namespaces in the order it
happens to encounter them - which varies with the hash seed of the run,
changing lines all over the output. Only the prefixes of the namespaces a
vocabulary actually uses appear in its serialization, so the entries that
never match are harmless; a namespace without an entry falls back to the
``ns`` numbering of :func:`export_turtle`.
"""

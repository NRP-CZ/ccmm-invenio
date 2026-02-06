#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

from pathlib import Path

from lxml.etree import fromstring

from ccmm_invenio.parsers.production_1_1_0 import CCMMXMLProductionParser
from tests.model import production_dataset

vocab_items = {
    "titletypes": {"https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/translatedTitle": "translatedTitle"},
    "identifierschemes": {
        "https://doi.org/": "doi",
        "https://organization.cz/datasets/": "organization-specific-id",
        "https://ror.org/": "ror",
        "https://orcid.org/": "orcid",
    },
    "resourcetypes": {
        "https://vocabularies.coar-repositories.org/resource_types/c_ddb1/": "Dataset",
        "http://purl.org/coar/resource_type/c_18cf/": "Software",
        "http://purl.org/coar/resource_type/8KJG-QS0Y": "PhysicalObject",
        "http://purl.org/coar/resource_type/FF4C-28RK": "ObservationData",
    },
    "languages": {
        "http://publications.europa.eu/resource/authority/language/CES": "CES",
        "http://publications.europa.eu/resource/authority/language/ENG": "ENG",
    },
    "datetypes": {
        "https://vocabs.ccmm.cz/registry/codelist/TimeReference/Created": "Created",
        "https://vocabs.ccmm.cz/registry/codelist/TimeReference/Collected": "Collected",
    },
    "descriptiontypes": {"https://vocabs.ccmm.cz/registry/codelist/DescriptionType/abstract": "abstract"},
    "fileformats": {
        "https://op.europa.eu/web/eu-vocabularies/concept/-/resource?"
        "uri=http://publications.europa.eu/resource/authority/file-type/GPKG": "GPKG"
    },
    "mediatypes": {
        "https://op.europa.eu/web/eu-vocabularies/concept/-/resource?"
        "uri=http://publications.europa.eu/resource/authority/file-type/ZIP": "ZIP"
    },
    "checksumalgorithms": {
        "https://www.iana.org/go/rfc6920": "rfc6920",
    },
    "locationrelationtypes": {"https://vocabs.ccmm.cz/registry/codelist/LocationRelation/Collected": "Collected"},
    "resourceagentroletypes": {
        "https://vocabs.ccmm.cz/registry/codelist/AgentRole/DataManager": "DataManager",
        "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Creator": "Creator",
        "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Publisher": "Publisher",
    },
    "resourcerelationtypes": {
        "https://vocabs.ccmm.cz/registry/codelist/RelationType/IsReferencedBy": "IsReferencedBy",
        "https://vocabs.ccmm.cz/registry/codelist/RelationType/IsDerivedFrom": "IsDerivedFrom",
        "https://vocabs.ccmm.cz/registry/codelist/RelationType/HasMetadata": "HasMetadata",
    },
    "subjectschemes": {
        "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/": "Frascati",
        "https://inspire.ec.europa.eu/theme/": "INSPIRE",
    },
    "accessrights": {"https://vocabularies.coar-repositories.org/access_rights/c_abf2/": "OpenAccess"},
}


def test_parse_production_1_1_0(clean_strings):
    xml_file = Path(__file__).parent / "data" / "nma_1_1_0-2026-01-29.xml"
    root_el = fromstring(xml_file.read_bytes())

    def vocabulary_loader(vocabulary_type: str, iri: str) -> str:
        return vocab_items[vocabulary_type][iri]

    parser = CCMMXMLProductionParser(vocabulary_loader=vocabulary_loader)

    record = parser.parse(root_el)

    cleaned_record = clean_strings(record)

    cleaned_expected = clean_strings(
        {
            "metadata": {
                "title": "Kvalita ovzduší ve středních čechách 2024",
                "version": "1.0.23",
                "publication_date": "2025-04-27",
                "additional_titles": [
                    {
                        "title": "Air quality measurements in Central Bohemian Region in 2024.",
                        "type": {"id": "translatedTitle"},
                        "lang": {"id": "ENG"},
                    }
                ],
                "additional_descriptions": [
                    {
                        "description": "Tato datová sada obsahuje měření kvality "
                        "ovzduší ve středních Čechách v roce 2024.",
                        "type": {"id": "abstract"},
                        "lang": {"id": "CES"},
                    }
                ],
                "identifiers": [{"identifier": "10.5281/zenodo.17594128", "scheme": "doi"}],
                "creators": [
                    {
                        "role": {"id": "Creator"},
                        "person_or_org": {
                            "name": "Šimek, Miroslav",
                            "type": "personal",
                            "given_name": "Miroslav",
                            "family_name": "Šimek",
                            "identifiers": [{"identifier": "0000-0003-0852-6632", "scheme": "orcid"}],
                        },
                        "affiliations": [{"name": "Univerzita Karlova"}],
                    }
                ],
                "subjects": [
                    {"id": "Frascati:10511", "subject": "Environmentální vědy"},
                    {"subject": "kvalita ovzduší"},
                    {"id": "INSPIRE:EF", "subject": "Environmental monitoring facilities"},
                ],
                "funding": [
                    {
                        "funder": {"name": "Grantová agentura České republiky"},
                        "award": {
                            "title": {"en": "Program for air pollution research"},
                            "number": "https://doi.org/award-identifier",
                        },
                    }
                ],
                "related_resources": [
                    {
                        "title": "Směrnice Evropského parlamentu a Rady 2008/50/ES ze dne 21. května 2008 o "
                        "kvalitě vnějšího ovzduší a čistším ovzduší pro Evropu",
                        "identifiers": [
                            {"identifier": "http://data.europa.eu/eli/dir/2008/50/oj"},
                            {
                                "identifier": 'https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32008L0050"%26"qid=1754039487879'
                            },
                        ],
                        "relation_type": {"id": "IsReferencedBy"},
                        "resource_type": {"id": "Software"},
                    },
                    {
                        "title": "ENVI LVS1 Sampler pro odběr prašného aerosolu",
                        "identifiers": [
                            {
                                "identifier": "https://www.envitech-bohemia.cz/p/264/envi-lvs1-sampler-pro-odber-prasneho-aerosolu"
                            }
                        ],
                        "resource_type": {"id": "PhysicalObject"},
                    },
                    {
                        "title": "Kvalita ovzduší – aktuální hodinové údaje",  # noqa: RUF001
                        "identifiers": [
                            {"identifier": "https://opendata.chmi.cz/air_quality/now/data/"},
                            {"identifier": "https://opendata.chmi.cz/air_quality/"},
                        ],
                        "relation_type": {"id": "IsDerivedFrom"},
                        "resource_type": {"id": "ObservationData"},
                    },
                    {
                        "title": "Metadata datoivé sady INSPIRE – Kvalita ovzduší – přehledy (data) "  # noqa: RUF001
                        "na měřicích stanicích",
                        "identifiers": [
                            {
                                "identifier": "https://data.gov.cz/zdroj/datov%C3%A9-sady/00020699/c724d055011d82189bbfc3766ffd1eb7"
                            }
                        ],
                        "relation_type": {"id": "HasMetadata"},
                    },
                ],
                "resource_type": {"id": "Dataset"},
                "languages": [{"id": "CES"}, {"id": "ENG"}],
                "locations": {
                    "features": [
                        {
                            "place": "Středočeský kraj",
                            "identifiers": [
                                {"scheme": "iri", "identifier": "https://vdp.cuzk.gov.cz/vdp/ruian/vusc/27"}
                            ],
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [
                                        [13.394972457505816, 49.50127042751268],
                                        [15.585575400519133, 49.50127042751268],
                                        [15.585575400519133, 50.61421606255462],
                                        [13.394972457505816, 50.61421606255462],
                                        [13.394972457505816, 49.50127042751268],
                                    ]
                                ],
                            },
                            "description": "Collected",
                        }
                    ]
                },
                "dates": [
                    {"date": "2025-04-27", "type": {"id": "Created"}},
                    {"date": "2024-01-01", "type": {"id": "Collected"}},
                ],
                "rights": [
                    {
                        "link": "https://creativecommons.org/licenses/by/4.0/",
                        "title": {"en": "Attribution 4.0 International"},
                    }
                ],
            }
        }
    )

    assert cleaned_record == cleaned_expected


def test_load_production_1_1_0(app, clean_strings):
    xml_file = Path(__file__).parent / "data" / "nma_1_1_0-2026-01-29.xml"
    root_el = fromstring(xml_file.read_bytes())

    def vocabulary_loader(vocabulary_type: str, iri: str) -> str:
        return vocab_items[vocabulary_type][iri]

    parser = CCMMXMLProductionParser(vocabulary_loader=vocabulary_loader)

    record = parser.parse(root_el)
    production_dataset.RecordSchema().load(record)

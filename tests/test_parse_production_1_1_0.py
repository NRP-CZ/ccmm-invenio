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


def test_parse_production_1_1_0():
    xml_file = Path(__file__).parent / "data" / "nma_1_1_0-2025-10-25.xml"
    root_el = fromstring(xml_file.read_bytes())

    def vocabulary_loader(vocabulary_type: str, iri: str) -> str:
        return vocab_items[vocabulary_type][iri]

    parser = CCMMXMLProductionParser(vocabulary_loader=vocabulary_loader)

    record = parser.parse(root_el)

    assert record == {
        "metadata": {
            "iri": "https://organization.cz/dataset_server/dataset_id",
            "locations": [
                {
                    "bounding_boxes": [
                        {
                            "lowerCorner": [13.394972457505816, 49.50127042751268],
                            "upperCorner": [15.585575400519133, 50.61421606255462],
                        }
                    ],
                    "geometry": {
                        "geometry": b"<gml:MultiSurface "
                        b'xmlns:gml="http://www.opengis.net/gml/3.2" '
                        b'gml:id="MS.AU.2.27" '
                        b'srsName="http://www.opengis.net/def/crs/EPSG/0/5514" '
                        b'srsDimension="2">\n                '
                        b"<gml:surfaceMember>\n"
                        b"                    "
                        b'<gml:Polygon gml:id="S.AU.2.27.1">\n'
                        b"                        "
                        b"<gml:exterior>\n                            "
                        b"<gml:LinearRing>\n                                "
                        b"<gml:posList>-700345.18 -989088.81 -700397.4 -989124.72 -700413.72\n"
                        b"                                    "
                        b"-989135.06 -700460.36 -989161.37 -700464.2 -989163.4 -700499.66\n"
                        b"                                    "
                        b"-989177.78 -700543.38 -989185.44 -700547.56 -989186.17\n"
                        b"                                   "
                        b"-734005.2 -1034221.4 -734000.7 -1034206.55 -733990.88 -1034174.1\n"
                        b"                                    "
                        b"733982.57 -1034166.93 -733980.5 -1034165.15 -733970.63\n"
                        b"                                    "
                        b"-1034131.76 -733969.44 -1034127.73 -733973.52 -1034126.34\n"
                        b"                                    "
                        b"-733972.62 -1034123.26</gml:posList>\n"
                        b"                            "
                        b"</gml:LinearRing>\n"
                        b"                        "
                        b"</gml:exterior>\n"
                        b"                    "
                        b"</gml:Polygon>\n"
                        b"                "
                        b"</gml:surfaceMember>\n"
                        b"            "
                        b"</gml:MultiSurface>\n"
                        b"            "
                    },
                    "names": ["Středočeský kraj"],
                    "related_objects": [
                        {
                            "iri": "https://vdp.cuzk.gov.cz/vdp/ruian/vusc/27",
                            "title": "Středočeský kraj",
                        }
                    ],
                    "relation_type": {"id": "Collected"},
                }
            ],
            "provenances": [{}],
            "related_resources": [
                {
                    "iri": "http://data.europa.eu/eli/dir/2008/50/oj",
                    "resource_relation_type": {"id": "IsReferencedBy"},
                    "resource_type": {"id": "Software"},
                    "resource_url": 'https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32008L0050"%26"qid=1754039487879',
                    "title": "Směrnice Evropského parlamentu a Rady 2008/50/ES ze dne 21. května 2008 o kvalitě\n"
                    "            vnějšího ovzduší a čistším ovzduší pro Evropu",
                },
                {
                    "resource_type": {"id": "PhysicalObject"},
                    "resource_url": "https://www.envitech-bohemia.cz/p/264/envi-lvs1-sampler-pro-odber-prasneho-aerosolu",
                    "title": "ENVI LVS1 Sampler pro odběr prašného aerosolu",
                },
                {
                    "iri": "https://opendata.chmi.cz/air_quality/now/data/",
                    "resource_relation_type": {"id": "IsDerivedFrom"},
                    "resource_type": {"id": "ObservationData"},
                    "resource_url": "https://opendata.chmi.cz/air_quality/",
                    "title": "Kvalita ovzduší – aktuální hodinové údaje",  # noqa RUF001
                },
                {
                    "iri": "https://data.gov.cz/zdroj/datov%C3%A9-sady/00020699/c724d055011d82189bbfc3766ffd1eb7",
                    "resource_relation_type": {"id": "HasMetadata"},
                    "resource_url": "https://data.gov.cz/zdroj/datov%C3%A9-sady/00020699/c724d055011d82189bbfc3766ffd1eb7",
                    "title": "Metadata datoivé sady INSPIRE – Kvalita ovzduší – přehledy (data) na měřicích\n"  # noqa RUF001
                    "            stanicích",
                },
            ],
            "terms_of_use": {
                "access_rights": {"id": "OpenAccess"},
                "contact_points": [
                    {
                        "person": {
                            "contact_points": [
                                {
                                    "emails": ["pavlina.dolezalova@organizace.cz"],
                                    "phones": ["+420784512963"],
                                }
                            ],
                            "name": "Pavlína Doležalová",
                        }
                    }
                ],
                "description": [
                    {
                        "lang": "cs",
                        "value": "Textový popis toho, jak je možné s datovou sadou\n            nakládat.",
                    }
                ],
                "license": {
                    "iri": "https://creativecommons.org/licenses/by/4.0/",
                    "label": [{"lang": "en", "value": "Attribution 4.0 International"}],
                },
            },
            "time_references": [
                {
                    "time_instant": {"date_time": "2025-04-27T12:00:01+02:00"},
                    "date_type": {"id": "Created"},
                },
                {
                    "time_interval": {
                        "beginning": {"date": "2024-01-01"},
                        "end": {"date": "2024-12-31"},
                    },
                    "date_type": {"id": "Collected"},
                },
            ],
            "title": "Kvalita ovzduší ve středních čechách 2024",
            "validation_results": [{}],
            "version": "1.0.23",
            "publication_date": "2025-04-27",
            "additional_titles": [
                {
                    "title": "Air quality measurements in Central Bohemian Region in 2024.",
                    "type": {"id": "translatedTitle"},
                    "lang": "en",
                }
            ],
            "additional_descriptions": [
                {
                    "description": "Tato datová sada obsahuje měření kvality ovzduší ve středních Čechách v\n"
                    "            roce 2024.",
                    "type": {"id": "abstract"},
                    "lang": "und",
                }
            ],
            "identifiers": [
                {"identifier": "25.45321", "scheme": "doi"},
                {"identifier": "air-q-cb-25-23", "scheme": "organization-specific-id"},
            ],
            "creators": [
                {
                    "role": {"id": "Creator"},
                    "person_or_org": {
                        "name": "Novák",
                        "type": "personal",
                        "given_name": "Jan",
                        "family_name": "Novák",
                        "identifiers": [{"identifier": "0030-04X2-2030-4X26", "scheme": "orcid"}],
                    },
                    "affiliations": [{"name": "Univerzita Karlova"}],
                }
            ],
            "subjects": [
                {
                    "iri": "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/10000/10500/10509",
                    "classification_code": "10511",
                    "subject_scheme": {"id": "Frascati"},
                    "title": [{"lang": "cs", "value": "Environmentální vědy"}],
                },
                {"title": [{"lang": "cs", "value": "kvalita ovzduší"}]},
                {
                    "iri": "http://inspire.ec.europa.eu/theme/ef",
                    "classification_code": "EF",
                    "definition": [
                        {
                            "lang": "en",
                            "value": "Location and operation of environmental monitoring facilities\n"
                            "            includes observation and measurement of emissions, "
                            "of the state of environmental media\n"
                            "            and of other ecosystem parameters (biodiversity, "
                            "ecological conditions of vegetation,\n"
                            "            etc.) by or on behalf of public authorities.",
                        }
                    ],
                    "subject_scheme": {"id": "INSPIRE"},
                    "title": [{"lang": "en", "value": "Environmental monitoring facilities"}],
                },
            ],
            "funding": [
                {
                    "funder": {"name": "Grantová agentura České republiky"},
                    "award": {
                        "title": "Program for air pollution research",
                        "number": "https://doi.org/award-identifier",
                    },
                }
            ],
            "resource_type": {"id": "Dataset"},
            "languages": [{"id": "CES"}, {"id": "ENG"}],
        }
    }

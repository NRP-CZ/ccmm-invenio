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

from ccmm_invenio.parsers.nma_1_1_0 import CCMMXMLNMAParser
from tests.model import nma_dataset

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


def test_parse_nma_1_1_0(clean_strings):
    xml_file = Path(__file__).parent / "data" / "nma_1_1_0-2026-01-29.xml"
    root_el = fromstring(xml_file.read_bytes())

    parser = CCMMXMLNMAParser(vocabulary_loader=lambda vocab_type, iri: vocab_items[vocab_type][iri])

    record = parser.parse(root_el)

    cleaned_record = clean_strings(record)
    cleaned_expected = clean_strings(
        {
            "metadata": {
                "iri": "https://organization.cz/dataset_server/dataset_id",
                "alternate_titles": [
                    {
                        "alternate_title_type": {"id": "translatedTitle"},
                        "title": [
                            {
                                "lang": {"id": "en"},
                                "value": "Air quality measurements in Central Bohemian Region in 2024.",
                            }
                        ],
                    }
                ],
                "descriptions": [
                    {
                        "description_text": [
                            {
                                "lang": {"id": "cs"},
                                "value": "Tato datová sada obsahuje měření kvality ovzduší ve středních Čechách v\n"
                                "            "
                                "roce 2024.",
                            }
                        ],
                        "description_type": {"id": "abstract"},
                    }
                ],
                "distributions": [
                    {
                        "distribution_data_service": {
                            "iri": "https://gis.cenia.gov.cz/id/service/wms/chmu_ovzdusi",
                            "access_services": [
                                {
                                    "iri": "https://gis.cenia.gov.cz/id/service/wms/chmu_ovzdusi",
                                    "endpoint_urls": [
                                        {
                                            "iri": "https://gis.cenia.gov.cz/id/service/wms/chmu_ovzdusi",
                                            "title": "Endpoint of WMS service Air quality",
                                        }
                                    ],
                                }
                            ],
                            "description": [
                                {
                                    "lang": {"id": "cs"},
                                    "value": "Prohlížecí služba (WMS) byla vytvořena na základě dat ČHMÚ a\n"
                                    "                "
                                    "obsahuje vrstvy: 1) Zóny a aglomerace hodnocení "
                                    "a řízení kvality ovzduší; 2) Státní\n"
                                    "                "
                                    "síť imisního monitoringu; 3) Pole koncentrací látek "
                                    "znečišťující ovzduší v gridu 1x1\n"
                                    "                "
                                    "km (Imisní limity pro ochranu lidského zdraví; "
                                    "Imisní limity pro ochranu ekosystémů\n"
                                    "                "
                                    "a vegetace); 4) Přehledy (data) naměřené na stanicích Státní imisní sítě\n"
                                    "                "
                                    "(Koncentrace látek znečišťujících ovzduší, pro "
                                    "které jsou stanoveny imisní limity\n"
                                    "                "
                                    "pro ochranu lidského zdraví; Koncentrace polutantů, "
                                    "pro které jsou stanoveny imisní\n"
                                    "                "
                                    "limity pro ochranu ekosystémů a vegetace) pro rok 2023.",
                                }
                            ],
                            "documentations": [
                                {
                                    "iri": "https://geoportal.gov.cz/web/guest/catalogue-client;jsessionid=F54A364E040A9D2184E42D94D288851C/"
                                }
                            ],
                            "conforms_to_specifications": [
                                {
                                    "iri": "",
                                    "label": [
                                        {
                                            "lang": {"id": "cs"},
                                            "value": "NAŘÍZENÍ KOMISE (ES) č. 976/2009 ze dne 19. října 2009, kterým\n"
                                            "                    "
                                            "se provádí směrnice Evropského parlamentu a Rady 2007/2/ES, "
                                            "pokud jde o síťové\n"
                                            "                    "
                                            "služby",
                                        }
                                    ],
                                }
                            ],
                            "title": "Služba WMS pro prohlížení dat o kvalitě ovzduší",
                        }
                    },
                    {
                        "distribution_downloadable_file": {
                            "iri": "http://portal.chmi.cz/AQ_DATA",
                            "access_urls": [
                                {
                                    "iri": "https://www.chmi.cz/o-nas/organizacni-struktura/usek-kvality-ovzdusi/oddeleni-informacniho-systemu-kvality-ovzdusi/odkazy",
                                    "label": [
                                        {
                                            "lang": {"id": "cs"},
                                            "value": "Oddělení informačního systému kvality ovzduší - odkazy",
                                        }
                                    ],
                                }
                            ],
                            "byte_size": 256,
                            "checksum": {
                                "algorithm": {"id": "rfc6920"},
                                "checksum_value": "9c56cc51b374d3a94e096e3f5483c05c6e69e221ae5d62a5435c5f3a9fc84938",
                            },
                            "conforms_to_schemas": [
                                {
                                    "iri": "https://inspire.ec.europa.eu/schemas/ef/4.0/EnvironmentalMonitoringFacilities.xsd",
                                    "label": [
                                        {
                                            "lang": {"id": "en"},
                                            "value": "Environmental monitoring facilities",
                                        }
                                    ],
                                }
                            ],
                            "download_urls": [
                                {
                                    "iri": "https://geoportal.gov.cz/atom/CHMU/chmu_ovzdusi_AQ_data_epsg4258_2023.zip",
                                    "label": [
                                        {
                                            "lang": {"id": "cs"},
                                            "value": "Datová sada ve formátu Geopackage",
                                        },
                                        {
                                            "lang": {"id": "en"},
                                            "value": "Dataset in Geopackage format",
                                        },
                                    ],
                                }
                            ],
                            "format": {"id": "GPKG"},
                            "media_type": {"id": "ZIP"},
                            "title": "Kvalita ovzduší",
                        }
                    },
                ],
                "funding_references": [
                    {
                        "iri": "https://funder-org.org/grants/123456789",
                        "award_title": "Program for air pollution research",
                        "funders": [
                            {
                                "organization": {
                                    "iri": "https://ror.org/01pv73b02",
                                    "identifiers": [{"value": "01pv73b02", "scheme": {"id": "ror"}}],
                                    "name": "Grantová agentura České republiky",
                                }
                            }
                        ],
                        "funding_program": "https://funder-org.org/program/abcdefgh",
                        "local_identifier": "https://doi.org/award-identifier",
                    }
                ],
                "identifiers": [
                    {
                        "iri": "https://doi.org/10.5281/zenodo.17594128",
                        "value": "10.5281/zenodo.17594128",
                        "scheme": {"id": "doi"},
                    }
                ],
                "locations": [
                    {
                        "bounding_boxes": [
                            {
                                "lowerCorner": [13.394972457505816, 49.50127042751268],
                                "upperCorner": [15.585575400519133, 50.61421606255462],
                            }
                        ],
                        "geometry": {
                            "geometry": b'<gml:MultiSurface xmlns:gml="http://www.opengis.net/gml/3.2"'
                            b' gml:id="MS.AU.2.27"'
                            b' srsName="http://www.opengis.net/def/crs/EPSG/0/5514"'
                            b' srsDimension="2">\n'
                            b"                "
                            b"<gml:surfaceMember>\n"
                            b"                    "
                            b'<gml:Polygon gml:id="S.AU.2.27.1">\n'
                            b"                        "
                            b"<gml:exterior>\n"
                            b"                            "
                            b"<gml:LinearRing>\n"
                            b"                                "
                            b"<gml:posList>"
                            b"-700345.18 -989088.81 -700397.4 -989124.72 -700413.72\n"
                            b"                                    "
                            b"-989135.06 -700460.36 -989161.37 -700464.2 -989163.4 -700499.66\n"
                            b"                                    "
                            b"-989177.78 -700543.38 -989185.44 -700547.56 -989186.17\n"
                            b"                                    "
                            b"-734005.2 -1034221.4 -734000.7 -1034206.55 -733990.88 -1034174.1\n"
                            b"                                    "
                            b"-733982.57 -1034166.93 -733980.5 -1034165.15 -733970.63\n"
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
                "metadata_identifications": [
                    {
                        "iri": "https://original-catalogue/dataset_metadata_id",
                        "conforms_to_standards": [
                            {
                                "iri": "https://www.iso.org/standard/80275.html",
                                "label": [
                                    {
                                        "lang": {"id": "und"},
                                        "value": "ISO 19115-1:2014/Amd 2:2020",
                                    }
                                ],
                            }
                        ],
                        "date_created": "2025-04-28",
                        "date_updated": "2025-07-25",
                        "languages": [{"id": "CES"}],
                        "original_repository": {"iri": "https://original-repository.cz"},
                        "qualified_relations": [
                            {
                                "relation": {
                                    "person": {
                                        "affiliations": [
                                            {
                                                "identifiers": [
                                                    {
                                                        "iri": "https://ror.org/024d6js02",
                                                        "value": "024d6js02",
                                                        "scheme": {"id": "ror"},
                                                    }
                                                ],
                                                "name": "Univerzita Karlova",
                                            }
                                        ],
                                        "contact_points": [
                                            {
                                                "addresses": [{"full_addresses": ["Dlouhá 15, 11000, Praha 1"]}],
                                                "emails": ["jan.novak@email.com"],
                                                "phones": ["+0112345678"],
                                            }
                                        ],
                                        "family_names": ["Novák"],
                                        "given_names": ["Jan"],
                                        "identifiers": [
                                            {
                                                "iri": "https://orcid.org/0030-04X2-2030-4X26",
                                                "value": "0030-04X2-2030-4X26",
                                                "scheme": {"id": "orcid"},
                                            }
                                        ],
                                        "name": "Novák",
                                    }
                                },
                                "role": {"id": "DataManager"},
                            }
                        ],
                    }
                ],
                "other_languages": [{"id": "ENG"}],
                "primary_language": {"id": "CES"},
                "provenances": [{}],
                "publication_year": 2025,
                "qualified_relations": [
                    {
                        "relation": {
                            "person": {
                                "affiliations": [
                                    {
                                        "identifiers": [
                                            {
                                                "iri": "https://ror.org/024d6js02",
                                                "value": "024d6js02",
                                                "scheme": {"id": "ror"},
                                            }
                                        ],
                                        "name": "Univerzita Karlova",
                                    }
                                ],
                                "contact_points": [
                                    {
                                        "addresses": [{"full_addresses": ["Dlouhá 15, 11000, Praha 1"]}],
                                        "emails": ["miroslav.simek@email.com"],
                                        "phones": ["+0112345678"],
                                    }
                                ],
                                "family_names": ["Šimek"],
                                "given_names": ["Miroslav"],
                                "identifiers": [
                                    {
                                        "iri": "https://orcid.org/0000-0003-0852-6632",
                                        "value": "0000-0003-0852-6632",
                                        "scheme": {"id": "orcid"},
                                    }
                                ],
                                "name": "Šimek, Miroslav",
                            }
                        },
                        "role": {"id": "Creator"},
                    },
                    {
                        "relation": {
                            "person": {
                                "affiliations": [
                                    {
                                        "identifiers": [
                                            {
                                                "iri": "https://ror.org/02j46qs45",
                                                "value": "02j46qs45",
                                                "scheme": {"id": "ror"},
                                            }
                                        ],
                                        "name": "Masarykova Univerzita",
                                    }
                                ],
                                "contact_points": [
                                    {
                                        "addresses": [{"full_addresses": ["Pražská 3, 60200, Brno"]}],
                                        "emails": ["256384@muni.cz"],
                                        "phones": ["+420876543219"],
                                    }
                                ],
                                "family_names": ["Janouch"],
                                "given_names": ["Ivan"],
                                "identifiers": [
                                    {
                                        "iri": "https://orcid.org/0023-0802-44X6-26X0",
                                        "value": "0023-0802-44X6-26X0",
                                        "scheme": {"id": "orcid"},
                                    }
                                ],
                                "name": "Ivan Janouch",
                            }
                        },
                        "role": {"id": "Publisher"},
                    },
                ],
                "related_resources": [
                    {
                        "iri": "http://data.europa.eu/eli/dir/2008/50/oj",
                        "resource_relation_type": {"id": "IsReferencedBy"},
                        "resource_type": {"id": "Software"},
                        "resource_url": 'https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32008L0050"%26"qid=1754039487879',
                        "title": "Směrnice Evropského parlamentu a Rady 2008/50/ES ze dne 21. května 2008 o kvalitě\n"
                        "            "
                        "vnějšího ovzduší a čistším ovzduší pro Evropu",
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
                        "title": "Kvalita ovzduší – aktuální hodinové údaje",  # noqa: RUF001
                    },
                    {
                        "iri": "https://data.gov.cz/zdroj/datov%C3%A9-sady/00020699/c724d055011d82189bbfc3766ffd1eb7",
                        "resource_relation_type": {"id": "HasMetadata"},
                        "resource_url": "https://data.gov.cz/zdroj/datov%C3%A9-sady/00020699/c724d055011d82189bbfc3766ffd1eb7",
                        "title": "Metadata datoivé sady INSPIRE – Kvalita ovzduší – přehledy (data) na měřicích\n"  # noqa: RUF001
                        "            stanicích",
                    },
                ],
                "resource_type": {"id": "Dataset"},
                "subjects": [
                    {
                        "iri": "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/10000/10500/10509",
                        "classification_code": "10511",
                        "subject_scheme": {"id": "Frascati"},
                        "title": [{"lang": {"id": "cs"}, "value": "Environmentální vědy"}],
                    },
                    {"title": [{"lang": {"id": "cs"}, "value": "kvalita ovzduší"}]},
                    {
                        "iri": "http://inspire.ec.europa.eu/theme/ef",
                        "classification_code": "EF",
                        "definition": [
                            {
                                "lang": {"id": "en"},
                                "value": "Location and operation of environmental monitoring facilities\n"
                                "            "
                                "includes observation and measurement of emissions, "
                                "of the state of environmental media\n"
                                "            "
                                "and of other ecosystem parameters (biodiversity, ecological "
                                "conditions of vegetation,\n"
                                "            "
                                "etc.) by or on behalf of public authorities.",
                            }
                        ],
                        "subject_scheme": {"id": "INSPIRE"},
                        "title": [
                            {
                                "lang": {"id": "en"},
                                "value": "Environmental monitoring facilities",
                            }
                        ],
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
                            "lang": {"id": "cs"},
                            "value": "Textový popis toho, jak je možné s datovou sadou\n            nakládat.",
                        }
                    ],
                    "license": {
                        "iri": "https://creativecommons.org/licenses/by/4.0/",
                        "label": [
                            {
                                "lang": {"id": "en"},
                                "value": "Attribution 4.0 International",
                            }
                        ],
                    },
                },
                "time_references": [
                    {
                        "temporal_representation": {
                            "time_instant": {"date_time": "2025-04-27T12:00:01+02:00"},
                        },
                        "date_type": {"id": "Created"},
                    },
                    {
                        "temporal_representation": {
                            "time_interval": {
                                "beginning": {"date": "2024-01-01"},
                                "end": {"date": "2024-12-31"},
                            },
                        },
                        "date_type": {"id": "Collected"},
                    },
                ],
                "title": "Kvalita ovzduší ve středních čechách 2024",
                "validation_results": [{}],
                "version": "1.0.23",
            }
        }
    )

    assert cleaned_record == cleaned_expected


def test_load_nma_1_1_0(clean_strings):
    xml_file = Path(__file__).parent / "data" / "nma_1_1_0-2026-01-29.xml"
    root_el = fromstring(xml_file.read_bytes())

    parser = CCMMXMLNMAParser(vocabulary_loader=lambda vocab_type, iri: vocab_items[vocab_type][iri])

    record = parser.parse(root_el)
    nma_dataset.RecordSchema().load(record)

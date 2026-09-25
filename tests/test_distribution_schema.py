#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import ValidationError

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_xml_to_json,
)
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.distribution import file_distributions

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
# only the items used here, the vocabularies are big
VOCABULARIES = {
    "fileformats": ("v-ft", {"pdf", "tiff", "txt", "tar", "gpkg", "jpeg", "bin"}),
    "mediatypes": ("v-mt", {"application/pdf", "image/tiff", "text/plain", "application/zip", "image/jpeg"}),
    "checksumalgorithms": ("v-ca", {"sha256", "md5"}),
}


@pytest.fixture(scope="module")
def vocabularies(app, database, search):
    for vocabulary_type, (pid_type, ids) in VOCABULARIES.items():
        vocab_service.create_type(system_identity, vocabulary_type, pid_type)
        for entry in yaml.safe_load((FIXTURES / f"{vocabulary_type}.yaml").read_text(encoding="utf-8")):
            if entry["id"] in ids:
                vocab_service.create(system_identity, {"type": vocabulary_type, **entry})
    vocab_service.indexer.refresh()


def ccmm_distributions(sample: str) -> list:
    data, errors = convert_xml_to_json((SAMPLES_DIR / sample).read_text(encoding="utf-8"))
    assert errors == []
    return data["distribution"]


def load(distributions: list) -> list:
    return DatasetMetadataSchema(only=("distributions",)).load({"distribution": distributions})["distributions"]


def test_downloadable_file(vocabularies):
    distributions = load(ccmm_distributions("1m3t2-78951.xml"))
    assert len(distributions) == 12
    assert distributions[0] == {
        "distribution_downloadable_file": {
            "iri": "https://data.narodni-repozitar.cz/heyrovsky/datasets/1m3t2-78951/files/CebecauerTkadlec_GACR2026_MindMap.pdf",
            "title": "CebecauerTkadlec_GACR2026_MindMap.pdf",
            "access_urls": [{"iri": "https://data.narodni-repozitar.cz/heyrovsky/datasets/1m3t2-78951/files/"}],
            "download_urls": [
                {
                    "iri": "https://data.narodni-repozitar.cz/heyrovsky/datasets/1m3t2-78951/files/CebecauerTkadlec_GACR2026_MindMap.pdf",
                    "label": [{"lang": {"id": "eng"}, "value": "CebecauerTkadlec_GACR2026_MindMap.pdf"}],
                }
            ],
            "format": {"id": "pdf"},
            "media_type": {"id": "application/pdf"},
            "byte_size": 67587,
        }
    }


def test_vocabulary_iri_case(vocabularies):
    # vocabulary ids are lower case, an iri in the vocabulary namespace is found by the id
    (distribution,) = load(
        [
            {
                "distribution_downloadable_file": {
                    "title": "a.pdf",
                    "access_url": [{"iri": "https://x.cz/"}],
                    "format": {"iri": "http://publications.europa.eu/resource/authority/file-type/pdf"},
                    "media_type": {"iri": "http://www.iana.org/assignments/media-types/application/PDF"},
                    "byte_size": 1,
                    "checksum": {
                        "checksum_value": "9C56CC51",
                        "algorithm": {"iri": "http://spdx.org/rdf/terms#checksumAlgorithm_SHA256"},
                    },
                }
            }
        ]
    )
    file = distribution["distribution_downloadable_file"]
    assert file["format"] == {"id": "pdf"}
    assert file["media_type"] == {"id": "application/pdf"}
    assert file["checksum"] == {"checksum_value": "9C56CC51", "algorithm": {"id": "sha256"}}


def test_ccmm_sample_downloadable_file(vocabularies):
    (file_distribution,) = [d for d in ccmm_distributions("ccmm_sample.xml") if "distribution_downloadable_file" in d]
    file = load([file_distribution])[0]["distribution_downloadable_file"]
    assert file["format"] == {"id": "gpkg"}
    assert file["media_type"] == {"id": "application/zip"}
    # checksum_value is xs:hexBinary, decoded in upper case
    assert file["checksum"] == {
        "checksum_value": "9C56CC51B374D3A94E096E3F5483C05C6E69E221AE5D62A5435C5F3A9FC84938",
        "algorithm": {"id": "sha256"},
    }
    assert file["conforms_to_schemas"] == [
        {
            "iri": "https://inspire.ec.europa.eu/schemas/ef/4.0/EnvironmentalMonitoringFacilities.xsd",
            "label": [{"lang": {"id": "eng"}, "value": "Environmental monitoring facilities"}],
        }
    ]


@pytest.mark.parametrize(
    ("field", "iri"),
    [
        # a web page of the eu vocabulary, not the file type iri
        (
            "format",
            "https://op.europa.eu/web/eu-vocabularies/concept/-/resource?uri=http://publications.europa.eu/resource/authority/file-type/GPKG",
        ),
        # a file type is not a media type
        ("media_type", "http://publications.europa.eu/resource/authority/file-type/TAR"),
    ],
)
def test_unknown_vocabulary_iri(vocabularies, field, iri):
    file = {
        "title": "a.tar",
        "access_url": [{"iri": "https://x.cz/"}],
        "format": {"iri": "http://publications.europa.eu/resource/authority/file-type/TAR"},
        "byte_size": 1,
        field: {"iri": iri},
    }
    with pytest.raises(ValidationError) as e:
        load([{"distribution_downloadable_file": file}])
    assert "Could not find vocabulary" in str(e.value)


def test_data_service(vocabularies):
    (service_distribution,) = [d for d in ccmm_distributions("ccmm_sample.xml") if "distribution_data_service" in d]
    service = load([service_distribution])[0]["distribution_data_service"]
    assert service["title"] == "Služba WMS pro prohlížení dat o kvalitě ovzduší"
    assert service["access_services"] == [
        {
            "iri": "https://gis.cenia.gov.cz/id/service/wms/chmu_ovzdusi",
            "endpoint_urls": [
                {
                    "iri": "https://gis.cenia.gov.cz/id/service/wms/chmu_ovzdusi",
                    "title": "Endpoint of WMS service Air quality",
                }
            ],
        }
    ]
    (specification,) = service["conforms_to_specifications"]
    assert specification["iri"] == "http://data.europa.eu/eli/reg/2009/976/oj"
    assert specification["label"][0]["lang"] == {"id": "ces"}
    assert service["documentations"] == [
        {"iri": "https://geoportal.gov.cz/web/guest/catalogue-client;jsessionid=F54A364E040A9D2184E42D94D288851C/"}
    ]
    assert service["description"][0]["lang"] == {"id": "ces"}
    assert service["description"][0]["value"].startswith("Prohlížecí služba (WMS)")


def test_empty_application_profile_iri(vocabularies):
    # the iri is optional in the model (the label is required there), an empty <iri/> is dropped
    (service,) = load(
        [
            {
                "distribution_data_service": {
                    "title": "s",
                    "conforms_to_specification": [{"iri": None, "label": [{"lang": "en", "$": "a regulation"}]}],
                }
            }
        ]
    )
    assert service["distribution_data_service"]["conforms_to_specifications"] == [
        {"label": [{"lang": {"id": "eng"}, "value": "a regulation"}]}
    ]


def test_label_without_language(vocabularies):
    # an empty xml:lang ("no language") is the und (Undetermined) language, dumped back as an empty xml:lang
    distributions = load(
        [
            {
                "distribution_data_service": {
                    "title": "s",
                    "documentation": [{"iri": "https://x.cz/", "label": [{"lang": "", "$": "no language"}]}],
                }
            }
        ]
    )
    (documentation,) = distributions[0]["distribution_data_service"]["documentations"]
    assert documentation["label"] == [{"lang": {"id": "und"}, "value": "no language"}]
    (dumped,) = dump(distributions)
    assert dumped["distribution_data_service"]["documentation"][0]["label"] == [{"lang": "", "$": "no language"}]


def dump(distributions: list) -> list:
    return DatasetMetadataSchema(only=("distributions",)).dump({"distributions": distributions})["distribution"]


# ccmm_sample.xml has a data service and a downloadable file, the others downloadable files
@pytest.mark.parametrize("sample", ["1m3t2-78951.xml", "ccmm_sample.xml", "dmq82-ed856.xml"])
def test_round_trip(vocabularies, sample):
    distributions = load(ccmm_distributions(sample))
    dumped = dump(distributions)
    for distribution in dumped:
        _xml, errors = XMLToGenericJSONConverter().json_to_xml(
            ccmm_1_1_0_schema, distribution, f"{{{NS_CCMM_1_1_0}}}distribution"
        )
        assert errors == []
    # loading the dumped distributions gives the same distributions
    assert load(dumped) == distributions


def test_dump_downloadable_file(vocabularies):
    (file,) = dump(load(ccmm_distributions("1m3t2-78951.xml"))[:1])
    file = file["distribution_downloadable_file"]
    # the vocabulary iris are dumped from the exactMatch mappings, the labels from the vocabulary titles
    assert file["format"] == {
        "iri": "http://publications.europa.eu/resource/authority/file-type/PDF",
        "label": [{"lang": "en", "$": "PDF"}],
    }
    assert file["media_type"]["iri"] == "http://www.iana.org/assignments/media-types/application/pdf"
    assert file["access_url"] == [{"iri": "https://data.narodni-repozitar.cz/heyrovsky/datasets/1m3t2-78951/files/"}]
    assert file["download_url"][0]["label"] == [{"lang": "en", "$": "CebecauerTkadlec_GACR2026_MindMap.pdf"}]


def test_dump_data_service(vocabularies):
    (service_distribution,) = [d for d in ccmm_distributions("ccmm_sample.xml") if "distribution_data_service" in d]
    (service,) = dump(load([service_distribution]))
    # the dumped data service is the source one (xml:lang codes are the same, the text is kept)
    assert service == service_distribution


def test_local_files_dropped(vocabularies, app, monkeypatch):
    # the files of 1m3t2-78951.xml are all on data.narodni-repozitar.cz
    monkeypatch.setitem(app.config, "SITE_UI_URL", "https://data.narodni-repozitar.cz")
    data = {"distribution": ccmm_distributions("1m3t2-78951.xml")}
    assert DatasetMetadataSchema(only=("distributions",)).load(data) == {}


def test_local_file_by_api_url(vocabularies, app, monkeypatch):
    monkeypatch.setitem(app.config, "SITE_UI_URL", "https://repo.cz")
    monkeypatch.setitem(app.config, "SITE_API_URL", "https://repo.cz/api/")

    def file(access_url: str, download_url: str) -> dict:
        return {
            "distribution_downloadable_file": {
                "title": "a.pdf",
                "access_url": [{"iri": access_url}],
                "download_url": [{"iri": download_url}],
                "format": {"iri": "http://publications.europa.eu/resource/authority/file-type/PDF"},
                "byte_size": 1,
            }
        }

    local = file("https://other.cz/", "https://repo.cz/api/records/abc/files/a.pdf/content")
    lookalike = file("https://repo.cz.example.org/", "https://repo.czech.org/a.pdf")
    service = {"distribution_data_service": {"title": "s", "iri": "https://repo.cz/api/records/abc"}}
    loaded = load([local, lookalike, service])
    # only the local downloadable file is dropped; data services are always kept
    assert [d.get("distribution_downloadable_file", d.get("distribution_data_service"))["title"] for d in loaded] == [
        "a.pdf",
        "s",
    ]
    assert loaded[0]["distribution_downloadable_file"]["access_urls"] == [{"iri": "https://repo.cz.example.org/"}]


def test_exactly_one_distribution_kind(vocabularies):
    with pytest.raises(ValidationError):
        load(
            [
                {
                    "distribution_data_service": {"title": "s"},
                    "distribution_downloadable_file": {
                        "title": "f",
                        "byte_size": 1,
                        "access_url": [{"iri": "https://x.cz"}],
                        "format": {"iri": "http://publications.europa.eu/resource/authority/file-type/PDF"},
                    },
                }
            ]
        )
    with pytest.raises(ValidationError):
        load([{}])


@pytest.mark.parametrize(
    ("ext", "mimetype", "file_format", "media_type"),
    [
        ("pdf", "application/pdf", "pdf", "application/pdf"),  # the extension is the id
        ("jpg", "image/jpeg", "jpeg", "image/jpeg"),  # by props.FILE_EXT (".jpeg, .jpg")
        ("h5", "application/x-hdf5", "bin", None),  # not in the vocabularies - binary data, no media type
    ],
)
def test_file_distributions(vocabularies, ext, mimetype, file_format, media_type):
    entry = {"key": f"a b.{ext}", "size": 3, "checksum": "md5:abc123", "ext": ext, "mimetype": mimetype}
    (distribution,) = file_distributions(
        [entry], access_url="https://repo.cz/records/x", download_url=lambda key: f"https://repo.cz/{key}"
    )
    file = distribution["distribution_downloadable_file"]
    assert file["format"] == {"id": file_format}
    assert file.get("media_type") == ({"id": media_type} if media_type else None)
    assert file["checksum"] == {"checksum_value": "abc123", "algorithm": {"id": "md5"}}
    assert file["access_urls"] == [{"iri": "https://repo.cz/records/x"}]
    assert file["download_urls"] == [{"iri": f"https://repo.cz/a b.{ext}"}]
    # the distribution dumps to valid ccmm
    (dumped,) = dump([distribution])
    _xml, errors = XMLToGenericJSONConverter().json_to_xml(
        ccmm_1_1_0_schema, dumped, f"{{{NS_CCMM_1_1_0}}}distribution"
    )
    assert errors == []

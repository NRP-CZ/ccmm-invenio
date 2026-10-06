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
from marshmallow_utils.fields import EDTFDateTimeString

from ccmm_invenio.resources.serializers.ccmm.converter import convert_xml_to_json
from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema
from ccmm_invenio.resources.serializers.ccmm.schema.time_references import TimeReferenceSchema, TimeRepresentationField

FIXTURES = Path(__file__).parent.parent / "src/ccmm_invenio/fixtures" / "data"
SAMPLES_DIR = (
    Path(__file__).parent.parent / "ccmm_versions/ccmm-xml-releases/ccmm-1.1.0-2026-01-29/metadata-samples/xml"
)
CREATED = "https://vocabs.ccmm.cz/registry/codelist/TimeReference/Created"


@pytest.fixture(scope="module")
def date_types(app, database, search):
    vocab_service.create_type(system_identity, "datetypes", "dattyp")
    for entry in yaml.safe_load((FIXTURES / "datetypes.yaml").read_text(encoding="utf-8")):
        vocab_service.create(system_identity, {"type": "datetypes", **entry})
    vocab_service.indexer.refresh()


@pytest.mark.parametrize(
    ("ccmm", "edtf"),
    [
        ({"time_instant": {"date": "2025-04-03"}}, "2025-04-03"),
        ({"time_instant": {"date": "2025-04-03Z"}}, "2025-04-03"),
        ({"time_instant": {"date_time": "2025-04-27T12:00:01+02:00"}}, "2025-04-27T12:00:01+02:00"),
        (
            {"time_interval": {"beginning": {"date": "2024-01-01"}, "end": {"date": "2024-12-31"}}},
            "2024-01-01/2024-12-31",
        ),
        # RDM intervals are date-only
        (
            {"time_interval": {"beginning": {"date": "2024-01-01"}, "end": {"date_time": "2024-12-31T10:00:00Z"}}},
            "2024-01-01/2024-12-31",
        ),
    ],
)
def test_load_time_representation(ccmm, edtf):
    assert TimeRepresentationField().deserialize(ccmm) == edtf


@pytest.mark.parametrize(
    ("edtf", "ccmm"),
    [
        ("2025-04-03", {"time_instant": {"date": "2025-04-03"}}),
        ("2025-04-27T12:00:01+02:00", {"time_instant": {"date_time": "2025-04-27T12:00:01+02:00"}}),
        (
            "2024-01-01/2024-12-31",
            {"time_interval": {"beginning": {"date": "2024-01-01"}, "end": {"date": "2024-12-31"}}},
        ),
        # reduced precision becomes the interval it spans
        ("2025", {"time_interval": {"beginning": {"date": "2025-01-01"}, "end": {"date": "2025-12-31"}}}),
        ("2024-02", {"time_interval": {"beginning": {"date": "2024-02-01"}, "end": {"date": "2024-02-29"}}}),
        (
            "2020/2021-06",
            {"time_interval": {"beginning": {"date": "2020-01-01"}, "end": {"date": "2021-06-30"}}},
        ),
    ],
)
def test_dump_time_representation(edtf, ccmm):
    assert TimeRepresentationField().serialize("date", {"date": edtf}) == ccmm


def test_invalid_time_representation():
    with pytest.raises(ValidationError):
        TimeRepresentationField().deserialize({"time_instant": {}})
    with pytest.raises(ValidationError):
        TimeRepresentationField().deserialize({"something": {}})


@pytest.mark.parametrize("sample", sorted(SAMPLES_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_load_samples(date_types, sample):
    data, errors = convert_xml_to_json(sample.read_text(encoding="utf-8"))
    assert errors == []

    loaded = DatasetMetadataSchema(only=("dates",)).load(data)

    assert len(loaded["dates"]) == len(data["time_reference"])
    for date in loaded["dates"]:
        EDTFDateTimeString().deserialize(date["date"])  # valid for RDM
        assert date["type"]["id"]

    # dump and load again gives the same dates
    dumped = DatasetMetadataSchema(only=("dates",)).dump(loaded)
    assert DatasetMetadataSchema(only=("dates",)).load(dumped) == loaded


def test_ccmm_sample(date_types):
    data, _ = convert_xml_to_json((SAMPLES_DIR / "ccmm_sample.xml").read_text(encoding="utf-8"))
    assert DatasetMetadataSchema(only=("dates",)).load(data)["dates"] == [
        {"date": "2025-04-27T12:00:01+02:00", "type": {"id": "collected"}},
        {"date": "2024-01-01/2024-12-31", "type": {"id": "collected"}},
    ]


def test_date_information(date_types):
    ccmm = {
        "temporal_representation": {"time_instant": {"date": "2025-04-03"}},
        "date_type": {"iri": CREATED},
        "date_information": {"lang": "en", "$": "First version"},
    }
    loaded = TimeReferenceSchema().load(ccmm)
    assert loaded == {"date": "2025-04-03", "type": {"id": "created"}, "description": "First version"}
    # the language of the description is not known in invenio
    assert TimeReferenceSchema().dump(loaded)["date_information"] == {"lang": "", "$": "First version"}


@pytest.mark.parametrize(
    ("sample", "publication_date"),
    [
        ("dataset-mini.xml", "2024-05-01"),  # created date
        ("1m3t2-78951.xml", "2025-04-02/2025-04-03"),  # created interval
        ("ccmm_sample.xml", "2025-01-01"),  # no created date - publication year
    ],
)
def test_publication_date_from_created(date_types, sample, publication_date):
    data, _ = convert_xml_to_json((SAMPLES_DIR / sample).read_text(encoding="utf-8"))
    loaded = DatasetMetadataSchema(only=("dates", "publication_date")).load(data)
    assert loaded["publication_date"] == publication_date


def test_publication_date_from_created_date_time():
    schema = DatasetMetadataSchema()
    created = {"date": "2025-04-27T12:00:01+02:00", "type": {"id": "created"}}
    # publication_date can not have the time of day
    assert schema.use_created_date({"dates": [created]})["publication_date"] == "2025-04-27"

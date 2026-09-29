#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

import pytest
from marshmallow import ValidationError

from ccmm_invenio.resources.serializers.ccmm.schema.dataset import DatasetMetadataSchema, DatasetSchema

CES = {"iri": "http://publications.europa.eu/resource/authority/language/CES"}
ENG = {"iri": "http://publications.europa.eu/resource/authority/language/ENG"}
DEU = {"iri": "http://publications.europa.eu/resource/authority/language/DEU"}


def test_merge_languages():
    schema = DatasetMetadataSchema()
    assert schema.merge_languages({"primary_language": CES, "other_language": [ENG, DEU]}) == {
        "other_language": [CES, ENG, DEU]
    }
    assert schema.merge_languages({"primary_language": CES}) == {"other_language": [CES]}
    assert schema.merge_languages({"other_language": [ENG]}) == {"other_language": [ENG]}
    assert schema.merge_languages({}) == {}


def test_split_languages():
    schema = DatasetMetadataSchema()
    assert schema.split_languages({"other_language": [CES, ENG, DEU]}) == {
        "primary_language": CES,
        "other_language": [ENG, DEU],
    }
    assert schema.split_languages({"other_language": [CES]}) == {"primary_language": CES}
    assert schema.split_languages({"other_language": []}) == {}
    assert schema.split_languages({}) == {}


def test_publication_year():
    schema = DatasetMetadataSchema(only=("publication_date",))
    assert schema.load({"publication_year": "2025"}) == {"publication_date": "2025-01-01"}
    assert schema.load({"publication_year": "2025Z"}) == {"publication_date": "2025-01-01"}
    with pytest.raises(ValidationError):
        schema.load({"publication_year": "abc"})

    # dump: the year of the (EDTF) publication date
    assert schema.dump({"publication_date": "2024-05-01"}) == {"publication_year": "2024"}
    assert schema.dump({"publication_date": "2020/2021"}) == {"publication_year": "2020"}


def test_ccmm_xml_on_the_record():
    # the ccmm elements go to the record metadata, the source xml is kept next to it
    schema = DatasetSchema(only=("metadata.publication_date", "ccmm_xml"))
    loaded = schema.load({"publication_year": "2025", "ccmm_xml": "<xml/>"})
    assert loaded == {"metadata": {"publication_date": "2025-01-01"}, "ccmm_xml": "<xml/>"}
    assert schema.dump(loaded) == {"publication_year": "2025", "ccmm_xml": "<xml/>"}


def test_created_date_is_publication_date():
    schema = DatasetMetadataSchema()
    created = {"date": "2024-05-01", "type": {"id": "created"}}
    collected = {"date": "2023-01-01", "type": {"id": "collected"}}
    assert schema.use_created_date({"publication_date": "2025-01-01", "dates": [collected, created]}) == {
        "publication_date": "2024-05-01",
        "dates": [collected, created],
    }
    # no created date - the publication year is kept
    assert schema.use_created_date({"publication_date": "2025-01-01", "dates": [collected]})["publication_date"] == (
        "2025-01-01"
    )

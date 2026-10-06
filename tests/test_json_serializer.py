#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

import json

from ccmm_invenio.resources.serializers.json import JSONWithoutRelatedIdentifiersSerializer

RELATED_IDENTIFIER = {"identifier": "10.1234/abc", "scheme": "doi", "relation_type": {"id": "cites"}}


def record(record_id: str) -> dict:
    return {
        "id": record_id,
        "metadata": {"title": "A", "related_identifiers": [RELATED_IDENTIFIER], "related_resources": [{"title": "B"}]},
    }


def test_object():
    obj = record("a")
    serialized = json.loads(JSONWithoutRelatedIdentifiersSerializer().serialize_object(obj))
    assert serialized == {"id": "a", "metadata": {"title": "A", "related_resources": [{"title": "B"}]}}
    # the serialized object is not changed
    assert obj == record("a")


def test_list():
    obj_list = {"hits": {"hits": [record("a"), record("b")], "total": 2}, "links": {}}
    serialized = json.loads(JSONWithoutRelatedIdentifiersSerializer().serialize_object_list(obj_list))
    assert serialized["hits"]["total"] == 2
    assert [hit["metadata"] for hit in serialized["hits"]["hits"]] == [
        {"title": "A", "related_resources": [{"title": "B"}]}
    ] * 2

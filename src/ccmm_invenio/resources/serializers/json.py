#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""The JSON serializer (application/json) without the RDM related identifiers.

metadata.related_identifiers are derived from metadata.related_resources (see
ccmm_invenio.services.components.related_identifiers) for RDM (e.g. DataCite DOI registration, which
serializes the record, not the service result) - they are not shown to the API clients, the
related resources are. The stored record, the search index and the UI JSON (read only) keep them.
"""

from __future__ import annotations

from typing import Any, override

from flask_resources.serializers import JSONSerializer


def without_related_identifiers(record: Any) -> Any:
    """Return a copy of a dumped record without metadata.related_identifiers."""
    if not isinstance(record, dict) or not isinstance(record.get("metadata"), dict):
        return record
    return {**record, "metadata": {k: v for k, v in record["metadata"].items() if k != "related_identifiers"}}


def list_without_related_identifiers(record_list: Any) -> Any:
    """Return a copy of a dumped search result without the related identifiers of its hits."""
    hits = record_list.get("hits") if isinstance(record_list, dict) else None
    if not isinstance(hits, dict) or not isinstance(hits.get("hits"), list):
        return record_list
    return {**record_list, "hits": {**hits, "hits": [without_related_identifiers(hit) for hit in hits["hits"]]}}


class JSONWithoutRelatedIdentifiersSerializer(JSONSerializer):
    """The plain JSON serializer (application/json) without the related identifiers."""

    @override
    def serialize_object(self, obj: Any) -> str:
        return super().serialize_object(without_related_identifiers(obj))

    @override
    def serialize_object_list(self, obj_list: Any) -> str:
        return super().serialize_object_list(list_without_related_identifiers(obj_list))

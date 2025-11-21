#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""DataCite serializer for CCMM NMA records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import JSONSerializer
from invenio_rdm_records.resources.serializers.datacite import DataCite43Schema

if TYPE_CHECKING:
    from collections.abc import Mapping


class CCMMNMADataCiteJSONSerializer_1_1_0(MarshmallowSerializer):  # noqa: N801
    """Marshmallow based DataCite serializer for records."""

    def __init__(self, **options: Any):
        """Create a new instance of the serializer."""
        super().__init__(
            format_serializer_cls=JSONSerializer,
            object_schema_cls=NMADataCiteSchema,
            list_schema_cls=BaseListSchema,
            schema_kwargs={},
            **options,
        )


class NMADataCiteSchema(DataCite43Schema):
    """Schema for DataCite serialization of CCMM production records.

    TODO: this will not work correctly !!!
    """

    @override
    def get_locations(self, obj: Mapping[str, Any]) -> list:
        """Get locations."""
        return []

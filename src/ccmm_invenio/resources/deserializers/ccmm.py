#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""CCMM XML record deserializer."""

from __future__ import annotations

from typing import cast

from flask_resources.deserializers import DeserializerMixin
from marshmallow import ValidationError

from ..serializers.ccmm.converter import convert_xml_to_json
from ..serializers.ccmm.schema.dataset import DatasetSchema


class CCMMJSONDeserializer(DeserializerMixin):
    """CCMM 1.1.0 XML record deserializer, using the DatasetSchema conversion."""

    def deserialize(self, data: bytes) -> dict:
        """Deserialize data."""
        json_data, errors = convert_xml_to_json(data.decode("utf-8"))
        if errors or not isinstance(json_data, dict):
            raise ValidationError([str(error) for error in errors] or ["Not a valid CCMM dataset document"])
        return cast("dict", DatasetSchema().load(json_data))

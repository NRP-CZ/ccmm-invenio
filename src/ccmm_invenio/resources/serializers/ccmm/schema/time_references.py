#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm time reference <-> RDM EDTF date."""

from __future__ import annotations

import calendar
from typing import Any, override

from marshmallow import EXCLUDE, Schema, ValidationError, fields

from ccmm_invenio.resources.serializers.ccmm.schema.fields import TextWithoutLangField
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField


class TimeRepresentationField(fields.Field):
    """ccmm temporal_representation (time_instant or time_interval) <-> RDM EDTF date string.

    time_instant is a date_time (xs:dateTime) or a date (xs:date), time_interval has
    a beginning and an end, both time_instant.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, dict):
            raise ValidationError("Expected time_instant or time_interval")
        if "time_instant" in value:
            return self._load_instant(value["time_instant"])
        if "time_interval" in value:
            interval = value["time_interval"]
            # RDM (EDTF level 0) intervals are date-only - the time of day is dropped
            return "/".join(self._load_instant(interval.get(key) or {})[:10] for key in ("beginning", "end"))
        raise ValidationError("Expected time_instant or time_interval")

    @staticmethod
    def _load_instant(instant: dict[str, Any]) -> str:
        if instant.get("date_time"):
            return str(instant["date_time"])
        if instant.get("date"):
            # xs:date may have a timezone (2025-04-03Z), EDTF dates can not
            return str(instant["date"])[:10]
        raise ValidationError("Expected date_time or date")

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        if "/" in value:
            beginning, end = value.split("/")
        elif "T" not in value and len(value) < len("2025-01-01"):
            # reduced precision (2025, 2025-04): ccmm has only full dates, use the interval it spans
            beginning, end = value, value
        else:
            return {"time_instant": self._dump_instant(value)}
        return {
            "time_interval": {
                "beginning": self._dump_instant(beginning),
                "end": self._dump_instant(end, end=True),
            }
        }

    @staticmethod
    def _dump_instant(value: str, *, end: bool = False) -> dict[str, str]:
        if "T" in value:
            return {"date_time": value}
        if len(value) == len("2025"):
            value += "-12-31" if end else "-01-01"
        elif len(value) == len("2025-04"):
            last_day = calendar.monthrange(int(value[:4]), int(value[5:7]))[1]
            value += f"-{last_day:02d}" if end else "-01"
        return {"date": value}


class TimeReferenceSchema(Schema):
    """CCMM time reference <-> RDM date.

    Types as in invenio_rdm_records.services.schemas.metadata.DateSchema.
    """

    class Meta:
        """Schema options."""

        # iri (0..1), also iri of the time instant/interval: no counterpart in invenio
        unknown = EXCLUDE

    # ccmm 1..1
    date = TimeRepresentationField(required=True, data_key="temporal_representation")

    # ccmm 1..1
    type = CCMMVocabularyField("datetypes", required=True, data_key="date_type")

    # ccmm 0..1 with xml:lang; RDM description has no language
    description = TextWithoutLangField(data_key="date_information")

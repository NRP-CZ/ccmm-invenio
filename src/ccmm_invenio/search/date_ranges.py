#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""CCMM index dumpers for date-or-interval fields."""

from __future__ import annotations

from typing import Any

from invenio_rdm_records.records.dumpers.edtf import EDTFListDumperExt
from invenio_records.dumpers import SearchDumperExt


class EDTFListToDateRangeDumperExt(EDTFListDumperExt):
    """Use RDM EDTF parsing with our key name."""

    def __init__(self, list_field: str, key: str):
        """Initialize with correct key name."""
        super().__init__(list_field, key)
        self.range_key = self.key  # pyright: ignore[reportAttributeAccessIssue]

    def load(self, data: dict[str, Any], record_cls: type) -> dict[str, Any]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Load data."""
        _ = record_cls
        return data


class CCMMDateRangesDumperExt(SearchDumperExt):
    """Apply the RDM EDTF list dumper to CCMM dates and related-resource dates."""

    def __init__(self):
        """Initialize RDM EDTF dumper."""
        super().__init__()
        self._dates_dumper = EDTFListToDateRangeDumperExt("metadata.dates", "date")

    def dump(self, record: Any, data: dict[str, Any]) -> dict[str, Any]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Dump date fields."""
        # metadata.dates[]
        self._dates_dumper.dump(record, data)

        # metadata.related_resources[].dates[]
        for related in data.get("metadata", {}).get("related_resources", []):
            self._dates_dumper.dump(record, {"metadata": {"dates": related["dates"]}})
        return data

    def load(self, data: dict[str, Any], record_cls: type) -> dict[str, Any]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Load."""
        _ = record_cls
        return data

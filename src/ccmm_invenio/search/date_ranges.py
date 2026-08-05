"""CCMM index dumpers for date-or-interval fields."""

from __future__ import annotations

from typing import Any

from invenio_rdm_records.records.dumpers.edtf import EDTFListDumperExt
from invenio_records.dumpers import SearchDumperExt


class EDTFListToDateRangeDumperExt(EDTFListDumperExt):
    """Use RDM EDTF parsing with our key name."""

    def __init__(self, list_field: str, key: str):
        super().__init__(list_field, key)
        self.range_key = self.key

    def load(self, data: dict[str, Any], record_cls: type) -> dict[str, Any]:
        return data


class CCMMDateRangesDumperExt(SearchDumperExt):
    """Apply the RDM EDTF list dumper to CCMM dates and related-resource dates."""

    def __init__(self):
        super().__init__()
        self._dates_dumper = EDTFListToDateRangeDumperExt("metadata.dates", "date")

    def dump(self, record: Any, data: dict[str, Any]) -> dict[str, Any]:
        # metadata.dates[]
        self._dates_dumper.dump(record, data)

        # metadata.related_resources[].dates[]
        for related in data.get("metadata", {}).get("related_resources", []):
            self._dates_dumper.dump(record, {"metadata": {"dates": related["dates"]}})
        return data

    def load(self, data: dict[str, Any], record_cls: type) -> dict[str, Any]:
        return data
#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Subjects CSV reader for Invenio subjects vocabulary."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from .base import VocabularyReader

if TYPE_CHECKING:
    from pathlib import Path


class RDMSubjectsCSVReader(VocabularyReader):
    """Read CCMM SubjectCategory CSV and convert to RDM subjects vocabulary format."""

    def __init__(self, name: str, csv_path: Path) -> None:
        """Initialize the reader."""
        super().__init__(name)
        self.csv_path = csv_path

    def data(self) -> list[dict[str, object]]:
        """Convert CCMM CSV to Invenio subjects vocabulary YAML format."""
        with self.csv_path.open(encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')
            rows = list(reader)

        converted_data: list[dict[str, object]] = []
        for _row in rows:
            row = {key.strip(): value.strip() for key, value in _row.items() if key}

            term_id = row.get("id")
            iri = row.get("IRI")
            base_iri = row.get("base IRI")
            title_cs = row.get("title_cs")
            title_en = row.get("title_en")

            if not term_id or (not title_cs and not title_en):
                continue

            props: dict[str, str | None] = {
                "iri": iri,
            }
            if base_iri:
                props["base_iri"] = base_iri

            term: dict[str, object] = {
                "id": term_id,
                "scheme": "frascati",
                "subject": title_en or title_cs,
                "title": {
                    "cs": title_cs or title_en,
                    "en": title_en or title_cs,
                },
                "props": props,
            }

            converted_data.append(term)

        return converted_data

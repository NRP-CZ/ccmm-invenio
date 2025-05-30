import csv
from pathlib import Path
from typing import Any

from .base import VocabularyReader


class CSVReader(VocabularyReader):
    """Read CCMM CSV files and convert them to YAML format."""

    def __init__(self, name: str, csv_path: Path):
        super().__init__(name)
        self.csv_path = csv_path

    def data(self) -> list[dict[str, str]]:
        """Convert CCMM CSV to YAML that can be imported to NRP Invenio."""

        with open(self.csv_path, "r", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";", quotechar='"')
            rows = list(reader)

        # Remove leading and trailing whitespace from all keys and values
        converted_data: list[dict[str, str]] = []
        for row in rows:
            row = {key.strip(): value.strip() for key, value in row.items() if key}

            # IRI;base IRI;parentId;id;title_cs;title_en;definition_cs;definition_en
            term_id = row.pop("id")
            iri = row.pop("IRI")
            base_iri = row.pop("base IRI")
            parent_id = row.pop("parentId")
            title_cs = row.pop("title_cs")
            title_en = row.pop("title_en")
            definition_cs = row.pop("definition_cs")
            definition_en = row.pop("definition_en")

            if not term_id or (not title_cs and not title_en):
                # Skip empty rows
                continue

            term: dict[str, Any] = {
                "id": term_id,
                "title": {
                    "cs": title_cs,
                    "en": title_en,
                },
                "description": {
                    "cs": definition_cs,
                    "en": definition_en,
                },
                "props": {
                    "iri": iri,
                    "base_iri": base_iri,
                },
            }
            if parent_id:
                term["hierarchy"] = {
                    "parent": parent_id,
                }
            converted_data.append(term)
        return converted_data

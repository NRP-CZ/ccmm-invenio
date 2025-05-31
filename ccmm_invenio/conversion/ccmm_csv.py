import csv
from pathlib import Path
from typing import Any

from .base import VocabularyReader


class CSVReader(VocabularyReader):
    """Read CCMM CSV files and convert them to YAML format."""

    def __init__(
        self, name: str, csv_path: Path, extra: list[Path] | None = None
    ) -> None:
        super().__init__(name)
        self.csv_path = csv_path
        self.extra = extra or []

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

        converted_data_by_id = {term["id"]: term for term in converted_data}
        for extra_file in self.extra:
            with open(extra_file, "r", encoding="utf-8-sig") as extra_csv_file:
                extra_reader = csv.DictReader(
                    extra_csv_file, delimiter=";", quotechar='"'
                )
                for extra_row in extra_reader:
                    extra_row = {
                        key.strip(): value.strip()
                        for key, value in extra_row.items()
                        if key
                    }
                    term_id = extra_row.pop("id")
                    if term_id in converted_data_by_id:
                        converted = converted_data_by_id[term_id]
                        for k, v in extra_row.items():
                            # k might contain a dot that means nesting
                            _set(converted, k, v)
        return converted_data


def _set(d: dict[str, Any], key: str, value: str) -> None:
    """Set a value in a nested dictionary based on a dot-separated key."""
    keys = key.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value

from pathlib import Path
from typing import Any, Callable

import yaml

from .base import VocabularyReader


class FilterCls:
    """Base class for filter classes."""

    def __init__(self):
        pass

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Condition to filter items."""
        # Implement the filtering logic here
        return items


class FilteredReader(VocabularyReader):
    """Read and filter vocabulary data."""

    def __init__(
        self,
        name: str,
        input_file: Path,
        filter_cls: type[FilterCls] | Callable[[], FilterCls],
    ):
        """Initialize the reader."""
        super().__init__(name)
        self.input_file = input_file
        self.filter_cls = filter_cls

    def data(self):
        """Read the vocabulary data and apply the filter function."""
        with open(self.input_file, "r", encoding="utf-8") as file:
            _data = list(yaml.safe_load_all(file))

        # Apply the filter function
        flt = self.filter_cls()
        data = flt.filter(_data)

        # Remove hierarchy.parent from items that are not in the filtered list
        ids = {item["id"] for item in data}
        for item in data:
            if "hierarchy" in item and "parent" in item["hierarchy"]:
                parent = item["hierarchy"]["parent"]
                if parent not in ids:
                    del item["hierarchy"]

        return data


class DescendantsOfFilter(FilterCls):
    """Filter class to filter items based on descendants."""

    def __init__(self, descendants_of: set[str]):
        """Initialize the filter with a set of descendants."""
        super().__init__()
        self.descendants_of = descendants_of

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        known_parents: set[str] = set()

        # register initial known parents
        for item in items:
            iri = item.get("props", {}).get("iri")
            if iri and iri in self.descendants_of:
                known_parents.add(item["id"])

        ret: list[dict[str, Any]] = []
        for item in items:
            parent = item.get("hierarchy", {}).get("parent")
            if not parent:
                continue
            if parent in known_parents:
                known_parents.add(item["id"])
                ret.append(item)

        return ret

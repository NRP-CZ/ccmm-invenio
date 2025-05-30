from pathlib import Path

import yaml

from .base import VocabularyReader


class CopyReader(VocabularyReader):
    """Copy reader for copying vocabularies."""

    def __init__(self, name: str, input_file: Path):
        """Initialize the CopyReader."""
        super().__init__(name)
        self.input_file = input_file

    def data(self) -> list[dict[str, str]]:
        """Read the vocabulary from the input file."""
        with open(self.input_file, "r") as f:
            return list(yaml.safe_load_all(f))

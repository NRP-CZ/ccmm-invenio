from typing import Any


class VocabularyReader:
    """Base class for all readers."""

    def __init__(self, name: str):
        """Initialize the reader with a name."""
        self.name = name

    def data(self) -> list[dict[str, Any]]:
        """Read the data from the source."""
        raise NotImplementedError("Subclasses must implement this method.")

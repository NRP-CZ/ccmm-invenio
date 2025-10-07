#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Read and filter vocabulary data."""

from __future__ import annotations

from typing import Any


class VocabularyReader:
    """Base class for all readers."""

    def __init__(self, name: str):
        """Initialize the reader with a name."""
        self.name = name

    def data(self) -> list[dict[str, Any]]:
        """Read the data from the source."""
        raise NotImplementedError("Subclasses must implement this method.")

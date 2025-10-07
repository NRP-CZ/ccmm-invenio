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

from typing import TYPE_CHECKING

import yaml

from .base import VocabularyReader

if TYPE_CHECKING:
    from pathlib import Path


class CopyReader(VocabularyReader):
    """Copy reader for copying vocabularies."""

    def __init__(self, name: str, input_file: Path):
        """Initialize the CopyReader."""
        super().__init__(name)
        self.input_file = input_file

    def data(self) -> list[dict[str, str]]:
        """Read the vocabulary from the input file."""
        with self.input_file.open() as f:
            return list(yaml.safe_load_all(f))

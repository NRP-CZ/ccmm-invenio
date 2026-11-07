# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Input deserializers for CCMM Invenio records."""

from __future__ import annotations

from .ccmm import CCMMJSONDeserializer
from .datacite import DataCiteJSONDeserializer

__all__ = [
    "CCMMJSONDeserializer",
    "DataCiteJSONDeserializer",
]

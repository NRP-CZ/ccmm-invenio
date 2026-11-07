# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Service components of the ccmm models."""

from __future__ import annotations

from .related_identifiers import RelatedIdentifiersComponent
from .root_record import RootRecordComponent

__all__ = [
    "RelatedIdentifiersComponent",
    "RootRecordComponent",
]

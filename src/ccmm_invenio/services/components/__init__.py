#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Service components of the ccmm models."""

from __future__ import annotations

from .related_identifiers import RelatedIdentifiersComponent
from .root_record import RootRecordComponent

__all__ = [
    "RelatedIdentifiersComponent",
    "RootRecordComponent",
]

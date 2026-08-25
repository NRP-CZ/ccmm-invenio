#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Serializers for CCMM Invenio records."""

from __future__ import annotations

from .nma.datacite import CCMMNMADataCiteJSONSerializer_1_1_0
from .production.datacite import CCMMProductionDataCiteJSONSerializer_1_1_0

__all__ = [
    "CCMMNMADataCiteJSONSerializer_1_1_0",
    "CCMMProductionDataCiteJSONSerializer_1_1_0",
]

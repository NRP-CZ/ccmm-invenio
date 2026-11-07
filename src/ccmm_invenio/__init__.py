# SPDX-FileCopyrightText: 2025-2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""ccmm-invenio package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .idutils_ark import patch_idutils_ark

try:
    __version__ = version("ccmm-invenio")
except PackageNotFoundError:
    __version__ = "0.0.0dev0+unknown"

# temporary, until idutils supports https ARK URLs, their normalization and landing URLs
patch_idutils_ark()

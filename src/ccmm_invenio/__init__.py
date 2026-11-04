#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
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

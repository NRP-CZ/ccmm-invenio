#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Invenio module for CCMM Invenio UI webpack bundle."""

from __future__ import annotations

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    ".",
    default="semantic-ui",
    themes={
        "semantic-ui": {
            # TODO: Hacky way for JS tests to work. Our logic in runner looks only at entry points and here
            # we just have an alias. Should be fixed upstream
            "entry": {"ccmm_invenio": "./js/ccmm_invenio/index.js"},
            "dependencies": {},
            "devDependencies": {},
            "aliases": {"@js/ccmm_invenio": "./js/ccmm_invenio"},
        }
    },
)

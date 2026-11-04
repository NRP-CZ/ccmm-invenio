# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

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
            "entry": {
                "ccmm_invenio": "./js/ccmm_invenio/index.js",
                "ccmm_invenio_geolocations_css": "./less/ccmm_invenio/forms/ccmm_geolocations.less",
            },
            "dependencies": {
                "leaflet": "^1.9.4",
                "sanitize-html": "2.13.0",
                "@terraformer/wkt": "^2.2.2",
                "@geoman-io/leaflet-geoman-free": "^2.20.1",
            },
            "devDependencies": {},
            "aliases": {"@js/ccmm_invenio": "./js/ccmm_invenio"},
        }
    },
)

# -*- coding: utf-8 -*-
"""Webpack bundle for i18n support."""

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    ".",
    default="semantic-ui",
    themes={
        "semantic-ui": {
            "entry": {},
            "dependencies": {},
            "devDependencies": {},
            "aliases": {"@translations/ccmm_invenio": "translations/ccmm_invenio/i18next.js"},
        }
    },
)

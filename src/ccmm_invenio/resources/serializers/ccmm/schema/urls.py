#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Urls of this repository."""

from __future__ import annotations

from flask import current_app


def is_local_url(url: str) -> bool:
    """Return True if the url is on this server (SITE_UI_URL or SITE_API_URL).

    The site url itself or anything below it - not e.g. https://site.cz.example.org.
    """
    sites = [
        site.rstrip("/")
        for site in (current_app.config.get("SITE_UI_URL"), current_app.config.get("SITE_API_URL"))
        if site
    ]
    return any(url == site or url.startswith(f"{site}/") for site in sites)

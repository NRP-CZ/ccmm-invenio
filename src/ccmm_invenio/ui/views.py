# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT
"""ccmm-invenio views module.

This module contains Flask blueprint creation for ccmm-invenio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Blueprint

if TYPE_CHECKING:
    from flask import Flask


def create_blueprint(_: Flask) -> Blueprint:
    """Create the ccmm-invenio blueprint to register templates."""
    return Blueprint(
        "ccmm_invenio_ui",
        __name__,
        template_folder="templates",
    )

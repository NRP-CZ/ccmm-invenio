# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""CCMM UI module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Blueprint

if TYPE_CHECKING:
    from flask import Flask

from ccmm_invenio.ui.config import CCMMRecordsUIResourceConfig
from ccmm_invenio.ui.resource import CCMMRecordsUIResource

__all__ = (
    "CCMMRecordsUIResource",
    "CCMMRecordsUIResourceConfig",
)


def create_blueprint(_: Flask) -> Blueprint:
    """Create the ccmm-invenio blueprint to register templates."""
    return Blueprint(
        "ccmm_invenio_ui",
        __name__,
        template_folder="templates",
    )

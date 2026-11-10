#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm-invenio views module.

This module contains Flask blueprint creation for ccmm-invenio.
"""

from flask import Blueprint


def create_blueprint(app):
    """Create the ccmm-invenio blueprint to register templates."""
    return Blueprint(
        "ccmm_invenio_ui",
        __name__,
        template_folder="templates",
    )

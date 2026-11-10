#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm-invenio extension module.

This module contains the main Flask extension for ccmm-invenio, which automatically registers
LOCATIONS_SIDEBAR_TEMPLATE into the sidebar (list given by APP_RDM_DETAIL_SIDE_BAR_TEMPLATES).
The default position of locations sidebar box is at the end of the list. To change it, you need to use
`configure_detail_sidebar` from `oarepo_config` package inside `invenio.cfg` of given repository.
"""

LOCATIONS_SIDEBAR_TEMPLATE = "ccmm_invenio/record_detail/side_bar/locations.html"


class CCMMInvenioUI:
    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        if not app.config.get("CCMM_INVENIO_LOCATIONS_SIDEBAR", True):
            return
        sidebar = list(app.config.get("APP_RDM_DETAIL_SIDE_BAR_TEMPLATES", []))
        if LOCATIONS_SIDEBAR_TEMPLATE not in sidebar:
            sidebar.append(
                LOCATIONS_SIDEBAR_TEMPLATE
            )  # Default position of locations sidebar box is at the end of the list.
            app.config["APP_RDM_DETAIL_SIDE_BAR_TEMPLATES"] = sidebar

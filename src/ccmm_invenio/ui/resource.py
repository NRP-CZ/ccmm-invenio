#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Resource class for CCMM record UI resources."""

from __future__ import annotations

from oarepo_rdm.ui.resource import RDMRecordsUIResource


class CCMMRecordsUIResource(RDMRecordsUIResource):
    """Base resource for CCMM UI resources."""

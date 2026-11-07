# SPDX-FileCopyrightText: 2025-2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

from __future__ import annotations

from oarepo_model.api import model

from ccmm_invenio.models import ccmm_preset_1_1_0

#
# the ccmm dataset model, as a repository defines it
#
ccmm_dataset = model(
    "ccmm_dataset",
    version="1.1.0",
    presets=[
        ccmm_preset_1_1_0,
    ],
    configuration={},
    types=[
        {
            "Metadata": {
                "properties": {
                    "title": {"type": "fulltext+keyword"},
                    "adescription": {"type": "keyword"},
                },
            },
        }
    ],
    metadata_type="Metadata",
    customizations=[],
)
ccmm_dataset.register()

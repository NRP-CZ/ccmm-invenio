#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
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

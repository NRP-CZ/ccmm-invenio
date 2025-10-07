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

from ccmm_invenio.models import ccmm_nma_preset, ccmm_production_preset

#
# ccmm production model to be used in repositories
#
production_dataset = model(
    "production_dataset",
    version="1.1.0",
    presets=[
        ccmm_production_preset,
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
production_dataset.register()

#
# ccmm model for the national metadata directory/aggregator (NMA)
#
nma_dataset = model(
    "nma",
    version="1.1.0",
    presets=[
        ccmm_nma_preset,
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
nma_dataset.register()

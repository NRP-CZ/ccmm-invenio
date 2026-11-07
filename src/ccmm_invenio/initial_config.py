#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Configuration defaults of ccmm-invenio, loaded by invenio-config (``invenio_config.module`` entry point).

They are loaded before ``invenio.cfg``, so a deployment can override them there.
"""

from __future__ import annotations

RELATED_RESOURCES_DATACITE_MAPPER = "ccmm_invenio.resources.deserializers.datacite:map_datacite"
"""The DataCite → CCMM metadata mapping used by the DataCite resolver of oarepo-related-resources."""

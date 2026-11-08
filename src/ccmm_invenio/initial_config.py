# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Configuration defaults of ccmm-invenio, loaded by invenio-config (``invenio_config.module`` entry point).

They are loaded before ``invenio.cfg``, so a deployment can override them there.
"""

from __future__ import annotations

CCMM_KEEP_UNKNOWN_FUNDER_ROR = False
"""Keep the ROR of a funder that is not in the funders vocabulary as its id on CCMM import.

Off by default: the record would fail relation validation. Turn it on only when a service component
creates the missing funders (from ROR) before the record is committed.
"""

RELATED_RESOURCES_DATACITE_MAPPER = "ccmm_invenio.related_resources.datacite:map_datacite"
"""The DataCite → CCMM metadata mapping used by the DataCite resolver of oarepo-related-resources."""

RELATED_RESOURCES_CROSSREF_MAPPER = "ccmm_invenio.related_resources.crossref:map_crossref"
"""The Crossref → CCMM metadata mapping used by the Crossref resolver of oarepo-related-resources."""

RELATED_RESOURCES_HANDLE_MAPPER = "ccmm_invenio.related_resources.handle:map_handle"
"""The Handle landing page → CCMM metadata mapping used by the Handle resolver of oarepo-related-resources."""

RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE = "dataset"
"""The resource type the related-resources mappings use when the source has none (Crossref, Handle) or an
unknown one (DataCite)."""

RELATED_RESOURCES_RECORD_UI_SCHEMA = (
    "ccmm_invenio.resources.serializers.ui.related_resources.CCMMRelatedResourceUISchema"
)
"""The UI schema oarepo-related-resources serializes the resolved related records with."""

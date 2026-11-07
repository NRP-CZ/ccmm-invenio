# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""The CCMM mappings of the oarepo-related-resources resolvers.

oarepo-related-resources only fetches the metadata of an identifier (DataCite, Crossref, Handle); the mapping
to the record metadata is the model's and is configured with ``RELATED_RESOURCES_<PROVIDER>_MAPPER`` (set by
`ccmm_invenio.initial_config`):

* DataCite: `ccmm_invenio.resources.deserializers.datacite.map_datacite` (also the ``datacite-json`` import),
* Crossref: `ccmm_invenio.related_resources.crossref.map_crossref`,
* Handle: `ccmm_invenio.related_resources.handle.map_handle`.
"""

from __future__ import annotations

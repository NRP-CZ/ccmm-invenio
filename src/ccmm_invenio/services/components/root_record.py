#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Service component keeping the source CCMM XML on the record."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from invenio_records_resources.services.records.components import ServiceComponent

if TYPE_CHECKING:
    from flask_principal import Identity
    from invenio_records.api import Record


class RootRecordComponent(ServiceComponent):
    """Keep the source CCMM XML in the root-level ccmm_xml field of the record."""

    def create(
        self,
        identity: Identity,
        data: dict | None = None,
        record: Record | None = None,
        errors: list | None = None,
        **kwargs: Any,
    ) -> None:
        """Inject parsed metadata to the record."""
        _, _, _ = identity, errors, kwargs
        if data is not None and record is not None:
            record["ccmm_xml"] = data.get("ccmm_xml", "")

    # ccmm_xml is outside metadata, not copied between the draft and the record by the
    # invenio metadata component - copied the same way here
    def publish(
        self, identity: Identity, draft: Record | None = None, record: Record | None = None, **kwargs: Any
    ) -> None:
        """Copy the source xml from the draft to the published record."""
        _, _ = identity, kwargs
        if draft is not None and record is not None:
            record["ccmm_xml"] = draft.get("ccmm_xml", "")

    def edit(
        self, identity: Identity, draft: Record | None = None, record: Record | None = None, **kwargs: Any
    ) -> None:
        """Copy the source xml from the record to its edit draft."""
        _, _ = identity, kwargs
        if draft is not None and record is not None:
            draft["ccmm_xml"] = record.get("ccmm_xml", "")

    def new_version(
        self, identity: Identity, draft: Record | None = None, record: Record | None = None, **kwargs: Any
    ) -> None:
        """Copy the source xml from the record to the draft of its new version."""
        _, _ = identity, kwargs
        if draft is not None and record is not None:
            draft["ccmm_xml"] = record.get("ccmm_xml", "")

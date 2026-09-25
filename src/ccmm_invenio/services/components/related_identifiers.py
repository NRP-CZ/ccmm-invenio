#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""RDM related identifiers made from the ccmm related resources.

The related resources (metadata.related_resources) are the source, the RDM related identifiers
(metadata.related_identifiers) are derived from them, so that RDM (DataCite export, the
landing page, ...) sees the relations as well.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from invenio_rdm_records.services.schemas.metadata import RelatedIdentifierSchema
from invenio_records_resources.services.records.components import ServiceComponent
from marshmallow import ValidationError

if TYPE_CHECKING:
    from flask_principal import Identity
    from invenio_records.api import Record

log = logging.getLogger(__name__)


def related_identifiers(related_resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the RDM related identifiers of the related resources.

    Every identifier of a related resource becomes one related identifier, and so do its iri
    and resource url (the scheme detected, e.g. a doi from https://doi.org/...), all with the
    relation type and resource type of the related resource. Related identifiers are
    validated by RDM (RelatedIdentifierSchema) - a related resource without a relation type
    (required in RDM) and an identifier RDM does not accept (a scheme not in
    RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES, an invalid value) give no related identifier.
    Duplicates are dropped.
    """
    schema = RelatedIdentifierSchema()
    ret: list[dict[str, Any]] = []
    for resource in related_resources:
        if not (relation_type := resource.get("relation_type")):
            continue
        common = {"relation_type": {"id": relation_type["id"]}}
        if resource_type := resource.get("resource_type"):
            common["resource_type"] = {"id": resource_type["id"]}
        candidates = [
            *({"identifier": i["identifier"], "scheme": i["scheme"]} for i in resource.get("identifiers") or []),
            *({"identifier": url} for url in (resource.get("iri"), resource.get("resource_url")) if url),
        ]
        for candidate in candidates:
            try:
                related_identifier = schema.load({**candidate, **common})
            except ValidationError as e:
                log.debug("Not a related identifier: %s, %s", candidate, e.messages)
                continue
            if related_identifier not in ret:
                ret.append(related_identifier)
    return ret


class RelatedIdentifiersComponent(ServiceComponent):
    """Overwrite metadata.related_identifiers with the ones of metadata.related_resources.

    Runs after the metadata component, on the metadata the record is saved with.
    """

    def create(self, identity: Identity, data: dict | None = None, record: Record | None = None, **kwargs: Any) -> None:
        """Set the related identifiers of a new record or draft."""
        _, _, _ = identity, data, kwargs
        self._set_related_identifiers(record)

    def update_draft(
        self, identity: Identity, data: dict | None = None, record: Record | None = None, **kwargs: Any
    ) -> None:
        """Set the related identifiers of an updated draft."""
        _, _, _ = identity, data, kwargs
        self._set_related_identifiers(record)

    def update(self, identity: Identity, data: dict | None = None, record: Record | None = None, **kwargs: Any) -> None:
        """Set the related identifiers of an updated record."""
        _, _, _ = identity, data, kwargs
        self._set_related_identifiers(record)

    @staticmethod
    def _set_related_identifiers(record: Record | None) -> None:
        """Overwrite the related identifiers of the record, remove them when there are none."""
        if record is None:
            return
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            return
        if identifiers := related_identifiers(metadata.get("related_resources") or []):
            metadata["related_identifiers"] = identifiers
        else:
            metadata.pop("related_identifiers", None)

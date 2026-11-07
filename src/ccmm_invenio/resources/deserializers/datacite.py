# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""The model's ``datacite-json`` import: a DataCite JSON document to a CCMM record.

The mapping itself is `ccmm_invenio.related_resources.datacite.map_datacite` (shared with the DataCite
resolver of oarepo-related-resources).
"""

from __future__ import annotations

import json

from flask import current_app
from flask_resources.deserializers import DeserializerMixin
from marshmallow import ValidationError
from oarepo_related_resources.resolvers.base import ResolverProblemLevel

from ccmm_invenio.related_resources.datacite import map_datacite

DATACITE_JSON_MIMETYPE = "application/vnd.datacite.datacite+json"


class DataCiteJSONDeserializer(DeserializerMixin):
    """The ``datacite-json`` import: a DataCite attributes object to a CCMM record.

    Unmapped values are logged and left out, like in the related-resources prefill; an error (an
    unparseable title or creators) fails the import.
    """

    def deserialize(self, data: str | bytes) -> dict:
        """Deserialize a DataCite JSON document - the attributes object or the REST API ``{"data": ...}``."""
        attributes = json.loads(data)
        if not isinstance(attributes, dict):
            raise ValidationError("Not a DataCite JSON object.")
        if isinstance(attributes.get("data"), dict):
            attributes = attributes["data"].get("attributes", {})
        metadata, problems = map_datacite(attributes)
        errors = [p.message for p in problems if p.level == ResolverProblemLevel.ERROR]
        if errors:
            raise ValidationError(errors)
        for problem in problems:
            current_app.logger.info("DataCite import: %s", problem.message)
        return {"metadata": metadata}

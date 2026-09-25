#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""CCMM XML serializer and the CCMM mimetype's conversion machinery.

The serializer (:class:`CCMMXMLSerializer`), the XML ↔ generic JSON converter and the
marshmallow schemas (the ``schema`` package) of the CCMM mimetype live in this package.
"""

from __future__ import annotations

import logging
from typing import Any, cast, override

from flask_resources.serializers import BaseSerializer
from invenio_access.permissions import system_identity
from invenio_base import invenio_url_for
from invenio_records.api import Record
from oarepo_runtime import current_runtime

from .converter import (
    CCMM_XML_MIMETYPE,
    NAMESPACES,
    NS_CCMM_1_1_0,
    NS_GML,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
    convert_json_to_xml,
    convert_xml_to_json,
)
from .schema.dataset import DatasetSchema
from .schema.distribution import file_distributions

__all__ = [
    "CCMM_XML_MIMETYPE",
    "NAMESPACES",
    "NS_CCMM_1_1_0",
    "NS_GML",
    "CCMMXMLSerializer",
    "XMLToGenericJSONConverter",
    "ccmm_1_1_0_schema",
    "convert_json_to_xml",
    "convert_xml_to_json",
]

log = logging.getLogger(__name__)


class CCMMXMLSerializer(BaseSerializer):
    """Invenio record -> CCMM 1.1.0 XML document (application/vnd.ccmm.research-data+xml).

    The ccmm_xml of the record is not exported as-is, the xml is always regenerated
    from the record metadata (the record may have been edited since the import).

    The files of the record are exported as downloadable file distributions, next to the
    distributions in the metadata - only those the reader may see, see _file_distributions.
    """

    @override
    def serialize_object(self, obj: dict[str, Any]) -> str:
        """Serialize a single record."""
        metadata = obj.get("metadata", {})
        if files := self._file_distributions(obj):
            metadata = {**metadata, "distributions": [*metadata.get("distributions", []), *files]}
        record = {
            "metadata": metadata,
            "ccmm_xml": obj.get("ccmm_xml"),
            # the access rights are made from them
            "access": obj.get("access"),
            "files": obj.get("files"),
            # the metadata record (metadata_identification) is made from them
            "created": obj.get("created") or getattr(obj, "created", None),
            "updated": obj.get("updated") or getattr(obj, "updated", None),
            "links": self._links(obj),
        }
        xml, errors = convert_json_to_xml(cast("dict[str, Any]", DatasetSchema().dump(record)))
        # export is best effort (the conversion is not lossless); import rejects an invalid xml
        for error in errors:
            log.warning("Can not serialize the record completely to CCMM XML: %s", error)
        return xml

    def _file_distributions(self, obj: dict[str, Any]) -> list[dict[str, Any]]:
        """Return the advertised files of the record as ccmm downloadable file distributions.

        The download url is the content link of the file, as in the files api
        (see invenio_rdm_records.services.config.WithFileLinks).
        """
        model = current_runtime.models_by_schema.get(obj.get("$schema", ""))
        if model is None or model.file_service is None or not obj.get("id"):
            return []
        if isinstance(obj, Record):
            entries, access_url = self._public_files(model, obj)
        else:
            # rest api: the result for the identity of the request, files.entries are there
            # only when the identity may read the files (FilesSchema read_files permission)
            entries = list(((obj.get("files") or {}).get("entries") or {}).values())
            access_url = (obj.get("links") or {}).get("self_html")
        advertised = [entry for entry in entries if not (entry.get("access") or {}).get("hidden")]
        if not advertised or not access_url:
            return []
        endpoint = f"{model.file_service.config.name_of_file_blueprint}.read_content"
        return file_distributions(
            advertised,
            access_url=access_url,
            download_url=lambda key: invenio_url_for(endpoint, pid_value=obj["id"], key=key),
        )

    def _public_files(self, model: Any, obj: Record) -> tuple[list[dict[str, Any]], str | None]:
        """Return the file entries and the landing page of a record from oai-pmh, if its files are public.

        oai-pmh serializes the record loaded from the search index and is harvested by anyone, so only
        the files of a public record with public files are advertised. The index has no file entries,
        they are read from the database.
        """
        access = obj.get("access") or {}
        if access.get("record") != "public" or access.get("files") != "public":
            return [], None
        record = model.record_cls.pid.resolve(obj["id"])
        entries = [
            {"key": key, "access": file_record.get("access"), **file_record.file.dumps()}
            for key, file_record in record.files.entries.items()
        ]
        links = model.service.links_item_tpl.expand(system_identity, record)
        return entries, links.get("self_html")

    def _links(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Return the links of the record - of the service result, or made for a record from oai-pmh."""
        if not isinstance(obj, Record):
            return obj.get("links") or {}
        model = current_runtime.models_by_schema.get(obj.get("$schema", ""))
        return model.service.links_item_tpl.expand(system_identity, obj) if model else {}

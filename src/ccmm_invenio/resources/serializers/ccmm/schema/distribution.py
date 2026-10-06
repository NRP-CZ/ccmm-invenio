#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Marshmallow schemas for CCMM distributions.

ccmm distribution (generic json of the xml) <-> CCMMDistribution of the model (ccmm.yaml),
both data services and downloadable files are loaded and dumped. Files themselves are uploaded
via the files API, not via metadata - the distribution element only describes them. There is
no RDM counterpart, the model follows ccmm.

Field names are the names of the model fields, data_key the names of the ccmm elements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import EXCLUDE, Schema, ValidationError, fields, missing, validate, validates_schema

from ccmm_invenio.resources.serializers.ccmm.schema.fields import (
    ApplicationProfileSchema,
    IriLabelSchema,
    MultilingualField,
)
from ccmm_invenio.resources.serializers.ccmm.schema.identifiers import vocabulary_item_exists
from ccmm_invenio.resources.serializers.ccmm.schema.urls import is_local_url
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

# namespaces of the vocabulary iris, the rest of the iri lower-cased is the vocabulary id
FILE_TYPE_PREFIX = "http://publications.europa.eu/resource/authority/file-type/"
MEDIA_TYPE_PREFIX = "http://www.iana.org/assignments/media-types/"
CHECKSUM_ALGORITHM_PREFIX = "http://spdx.org/rdf/terms#checksumAlgorithm_"


class EndpointSchema(Schema):
    """ccmm related resource as an endpoint url of a data service (CCMMRelatedResource in the model)."""

    class Meta:
        """Schema options."""

        # alternate_title, identifier, qualified_relation, resource_relation_type, resource_type,
        # time_reference: not used for endpoints
        unknown = EXCLUDE

    # ccmm 0..1
    iri = fields.String()

    # ccmm 0..1
    title = fields.String()

    # ccmm 0..1
    resource_url = fields.String()


class DataServiceSchema(IriLabelSchema):
    """ccmm data service (access service of a distribution)."""

    # ccmm 1..n
    endpoint_urls = fields.List(
        fields.Nested(EndpointSchema), required=True, validate=validate.Length(min=1), data_key="endpoint_url"
    )


class ChecksumSchema(Schema):
    """ccmm checksum."""

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 0..1
    iri = fields.String()

    # ccmm 1..1
    checksum_value = fields.String(required=True)

    # ccmm 1..1
    algorithm = CCMMVocabularyField("checksumalgorithms", id_prefix=CHECKSUM_ALGORITHM_PREFIX, required=True)


class DownloadableFileSchema(Schema):
    """ccmm distribution downloadable file."""

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 0..1
    iri = fields.String()

    # ccmm 1..1
    title = fields.String(required=True)

    # ccmm 1..n
    access_urls = fields.List(
        fields.Nested(IriLabelSchema), required=True, validate=validate.Length(min=1), data_key="access_url"
    )

    # ccmm 0..n
    download_urls = fields.List(fields.Nested(IriLabelSchema), data_key="download_url")

    # ccmm 0..n
    conforms_to_schemas = fields.List(fields.Nested(ApplicationProfileSchema), data_key="conforms_to_schema")

    # ccmm 1..1
    format = CCMMVocabularyField("fileformats", id_prefix=FILE_TYPE_PREFIX, required=True)

    # ccmm 0..1
    media_type = CCMMVocabularyField("mediatypes", id_prefix=MEDIA_TYPE_PREFIX)

    # ccmm 1..1
    byte_size = fields.Integer(required=True)

    # ccmm 0..1
    checksum = fields.Nested(ChecksumSchema)


class DataServiceDistributionSchema(Schema):
    """ccmm distribution data service."""

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 0..1
    iri = fields.String()

    # ccmm 1..1
    title = fields.String(required=True)

    # ccmm 0..n
    access_services = fields.List(fields.Nested(DataServiceSchema), data_key="access_service")

    # ccmm 0..n
    conforms_to_specifications = fields.List(
        fields.Nested(ApplicationProfileSchema), data_key="conforms_to_specification"
    )

    # ccmm 0..n
    documentations = fields.List(fields.Nested(IriLabelSchema), data_key="documentation")

    # ccmm 0..n, each with xml:lang
    description = MultilingualField()


class DistributionSchema(Schema):
    """ccmm distribution; exactly one of a data service or a downloadable file (xs:choice)."""

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    distribution_data_service = fields.Nested(DataServiceDistributionSchema)
    distribution_downloadable_file = fields.Nested(DownloadableFileSchema)

    @validates_schema
    def one_distribution_kind(self, data: dict[str, Any], **_kwargs: Any) -> None:
        """Check a distribution is exactly one of a data service or a downloadable file."""
        if bool(data.get("distribution_data_service")) == bool(data.get("distribution_downloadable_file")):
            raise ValidationError("Expected exactly one of a data service or a downloadable file")


class DistributionsField(fields.Nested):
    """List of ccmm distributions, without the downloadable files of this server.

    A downloadable file with an access or download url on this server (SITE_UI_URL, SITE_API_URL)
    is uploaded to this record, so it is not loaded - its metadata would be there twice.
    Data services are always loaded. When nothing is left, the field is not loaded at all.
    """

    def __init__(self, **kwargs: Any):
        """Create the field."""
        super().__init__(DistributionSchema, many=True, **kwargs)

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, partial: Any = None, **kwargs: Any) -> Any:
        if isinstance(value, list):  # anything else is reported as invalid by Nested
            value = [distribution for distribution in value if not self._is_local_file(distribution)]
            if not value:
                return missing
        return super()._deserialize(value, attr, data, partial=partial, **kwargs)

    @staticmethod
    def _is_local_file(distribution: Any) -> bool:
        """Return True for a downloadable file with an access or download url on this server."""
        file = distribution.get("distribution_downloadable_file") if isinstance(distribution, dict) else None
        if not isinstance(file, dict):
            return False
        return any(
            is_local_url(url.get("iri") or "")
            for url in [*(file.get("access_url") or []), *(file.get("download_url") or [])]
            if isinstance(url, dict)
        )


# ccmm format is 1..1 - "Binary data" when the format of a file is not known
FALLBACK_FILE_FORMAT = "bin"


def file_distributions(
    entries: Iterable[dict[str, Any]], access_url: str, download_url: Callable[[str], str]
) -> list[dict[str, Any]]:
    """Invenio file entries -> ccmm downloadable file distributions (in the model, see DistributionSchema).

    The entries are as in the record (files.entries values: key, size, checksum, mimetype, ext).
    access_url is the landing page of the record, download_url returns the content url of a file
    by its key. The caller must pass only the files that may be advertised.
    """
    distributions = []
    for entry in entries:
        file: dict[str, Any] = {
            "title": entry["key"],
            "access_urls": [{"iri": access_url}],
            "download_urls": [{"iri": download_url(entry["key"])}],
            "format": {"id": _file_format(entry.get("ext"), entry.get("mimetype"))},
            "byte_size": entry["size"],
        }
        if (mimetype := entry.get("mimetype")) and vocabulary_item_exists("mediatypes", mimetype):
            file["media_type"] = {"id": mimetype}
        # invenio checksum is "<algorithm>:<hex digest>", e.g. "md5:662d150c..."
        algorithm, _, value = (entry.get("checksum") or "").partition(":")
        if value and vocabulary_item_exists("checksumalgorithms", algorithm.lower()):
            file["checksum"] = {"checksum_value": value, "algorithm": {"id": algorithm.lower()}}
        distributions.append({"distribution_downloadable_file": file})
    return distributions


def _file_format(ext: str | None, mimetype: str | None) -> str:
    """Return the id of the file format (fileformats vocabulary) of a file with the extension and media type.

    The vocabulary ids are mostly the extensions ("pdf", "csv"), other extensions are looked up in
    props.FILE_EXT (".jpeg, .jpg"); of several formats with the extension (e.g. .xml), the one with
    the media type (props.IANA_MT) is preferred, then the shortest (most generic) id.
    """
    ext = (ext or "").lower()
    if not ext.isalnum():
        return FALLBACK_FILE_FORMAT
    if vocabulary_item_exists("fileformats", ext):
        return ext
    hits = list(
        vocab_service.scan(
            system_identity,
            params={"q": f'props.FILE_EXT:"{ext}"'},
            type="fileformats",
        )
    )
    if not hits:
        return FALLBACK_FILE_FORMAT
    mimetype_str = mimetype or ""
    hits.sort(key=lambda hit: (mimetype_str not in str((hit.get("props") or {}).get("IANA_MT", "")), len(hit["id"])))
    return cast("str", hits[0]["id"])

#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Marshmallow schemas for the CCMM dataset and the related resource."""

from __future__ import annotations

from typing import Any

from invenio_rdm_records.services.schemas.fields import SanitizedHTML
from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_dump, post_load, pre_dump, pre_load, validate
from marshmallow_utils.fields import SanitizedUnicode

from ccmm_invenio.resources.serializers.ccmm.schema.access import access_right, rdm_access
from ccmm_invenio.resources.serializers.ccmm.schema.agents import (
    CCMM_ROLE_CREATOR,
    CCMM_ROLE_PUBLISHER,
    ContributorSchema,
    CreatorSchema,
    PublisherField,
)
from ccmm_invenio.resources.serializers.ccmm.schema.distribution import DistributionsField
from ccmm_invenio.resources.serializers.ccmm.schema.fields import LanguageTextMixin, SingleItemListNested, SplitNested
from ccmm_invenio.resources.serializers.ccmm.schema.funding import FundingReferenceSchema
from ccmm_invenio.resources.serializers.ccmm.schema.identifiers import IdentifierSchema
from ccmm_invenio.resources.serializers.ccmm.schema.locations import LocationsField
from ccmm_invenio.resources.serializers.ccmm.schema.metadata_record import MetadataRecordSchema, metadata_records
from ccmm_invenio.resources.serializers.ccmm.schema.subjects import SubjectSchema
from ccmm_invenio.resources.serializers.ccmm.schema.terms_of_use import TermsOfUseSchema
from ccmm_invenio.resources.serializers.ccmm.schema.time_references import TimeReferenceSchema
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField


class AlternateTitleSchema(LanguageTextMixin, Schema):
    """CCMM alternate title <-> RDM additional title.

    Expects a single language variant of the title, use it with SplitNested.
    Types as in invenio_rdm_records.services.schemas.metadata.TitleSchema.
    """

    ccmm_element = "title"  # 1..n, here a single one
    text_field = "title"
    ccmm_element_many = True

    class Meta:
        """Schema options."""

        # iri (0..1): no counterpart in invenio
        unknown = EXCLUDE

    title = SanitizedUnicode(required=True, validate=validate.Length(min=3))

    # ccmm 0..1, but required in RDM - "other" when missing (dumped back as the ccmm Other type)
    type = CCMMVocabularyField("titletypes", data_key="alternate_title_type", load_default=lambda: {"id": "other"})


class DescriptionSchema(LanguageTextMixin, Schema):
    """CCMM description <-> RDM additional description.

    Types as in invenio_rdm_records.services.schemas.metadata.DescriptionSchema.
    """

    ccmm_element = "description_text"  # 1..1
    text_field = "description"

    class Meta:
        """Schema options."""

        # iri (0..1): no counterpart in invenio
        unknown = EXCLUDE

    description = SanitizedHTML(required=True, validate=validate.Length(min=3))

    # ccmm 0..1, but required in RDM - "other" when missing (dumped back as the ccmm Other type)
    type = CCMMVocabularyField("descriptiontypes", data_key="description_type", load_default=lambda: {"id": "other"})


class CommonResourceFieldsMixin:
    """Fields and hooks common to the ccmm dataset and related resource (mapped the same way to invenio).

    Field names are the names of the invenio fields, data_key the names of the ccmm elements.
    """

    # dataset 1..n, related resource 0..n
    identifiers = fields.Nested(IdentifierSchema, many=True, data_key="identifier")

    # ccmm 0..1; kept as it is (the iri of the source dataset / related resource). Not record pids -
    # those are minted by invenio (RDM_PERSISTENT_IDENTIFIERS, pidstore providers)
    iri = fields.String(data_key="iri")

    # dataset 1..1, related resource 0..1 (filled from the iri/resource url when missing, see default_title)
    title = fields.String(data_key="title")

    # 0..n; one alternate_title with multiple language variants of the title
    # becomes multiple additional_titles (one per language)
    additional_titles = SplitNested(AlternateTitleSchema, split_on="title", data_key="alternate_title")

    # dataset 1..n, related resource 0..n; RDM dates are single dates or range 2026-01-01/2027-01-01
    dates = fields.Nested(TimeReferenceSchema, many=True, data_key="time_reference")

    # 0..1
    resource_type = CCMMVocabularyField("resourcetypes", data_key="resource_type")

    # ccmm qualified_relation 0..n, split by the role (see split_qualified_relations):
    # Creator -> creators, Publisher -> publisher, any other role -> contributors
    creators = fields.Nested(CreatorSchema, many=True, data_key="qualified_relation[creator]")
    contributors = fields.Nested(ContributorSchema, many=True, data_key="qualified_relation[contributor]")
    publisher = PublisherField(data_key="qualified_relation[publisher]")

    @pre_load
    def split_qualified_relations(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Split ccmm qualified relations by their role to the creators, publisher and contributors keys."""
        if "qualified_relation" not in data:
            return data
        data = dict(data)
        for relation in data.pop("qualified_relation"):
            role = (relation.get("role") or {}).get("iri") if isinstance(relation, dict) else None
            key = {CCMM_ROLE_CREATOR: "creator", CCMM_ROLE_PUBLISHER: "publisher"}.get(role or "", "contributor")
            data.setdefault(f"qualified_relation[{key}]", []).append(relation)
        return data

    @post_dump
    def merge_qualified_relations(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Merge the dumped creators, publisher and contributors back to the ccmm qualified relations."""
        relations = [
            relation
            for key in ("creator", "publisher", "contributor")
            for relation in data.pop(f"qualified_relation[{key}]", None) or []
        ]
        if relations:
            data["qualified_relation"] = relations
        return data


class RelatedResourceSchema(CommonResourceFieldsMixin, Schema):
    """CCMM related resource <-> ccmm-invenio related resource (CCMMInvenioRelatedResource in the model)."""

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    # ccmm 0..1
    relation_type = CCMMVocabularyField("relationtypes", data_key="resource_relation_type")

    # ccmm 0..1; kept as it is
    resource_url = fields.String(data_key="resource_url")

    @post_load
    def default_title(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Use the iri or the resource url as the title of a related resource without one.

        The title is 0..1 in ccmm, but required in the model (CCMMInvenioRelatedResource).
        """
        if not data.get("title") and (title := data.get("iri") or data.get("resource_url")):
            data["title"] = title
        return data


class DatasetMetadataSchema(CommonResourceFieldsMixin, Schema):
    """Dataset metadata schema converter.

    Converts XML dataset records that were first converted to generic JSON format
    (see XMLToGenericJSONConverter) into the metadata of a standard ccmm-invenio dataset
    (the "metadata" part of the record). The fields common with the related resource are
    in CommonResourceFieldsMixin.

    Field names are the names of the invenio fields, data_key the names of the ccmm elements.
    """

    class Meta:
        """Schema options."""

        # the generic json contains elements that are not mapped (see "Not mapped" below)
        # and xml namespace declarations (xmlns, xsi:schemaLocation)
        unknown = EXCLUDE

    # ccmm 0..1
    version = fields.String(data_key="version")

    # ccmm 0..1; required in RDM - a ccmm dataset without a resource type is a dataset
    resource_type = CCMMVocabularyField(
        "resourcetypes", data_key="resource_type", load_default=lambda: {"id": "dataset"}
    )

    # ccmm 0..n; each ccmm description has a single language variant (description_text 1..1)
    additional_descriptions = fields.Nested(DescriptionSchema, many=True, data_key="description")

    # ccmm 1..1, gYear; RDM needs a full date: the date of the "Created" time_reference
    # takes precedence (see use_created_date), otherwise <publication_year>-01-01.
    # Dumped as the year of the publication date.
    publication_date = fields.Method(
        serialize="dump_publication_year",
        deserialize="load_publication_year",
        data_key="publication_year",
    )

    # ccmm 0..n other_language and 0..1 primary_language, the primary language goes first,
    # see merge_languages and split_languages
    languages = fields.List(CCMMVocabularyField("languages"), data_key="other_language")

    # ccmm 1..1; RDM rights is a list
    rights = SingleItemListNested(TermsOfUseSchema, data_key="terms_of_use")

    # ccmm 1..n; a subject from the subjects vocabulary becomes one RDM subject ({"id": ...}),
    # a keyword with multiple language variants of the title becomes one RDM subject per language
    subjects = SplitNested(SubjectSchema, split_on="title", unique=True, data_key="subject")

    # ccmm 0..n; RDM locations is an object with features, one feature per geometry (see LocationsField)
    locations = LocationsField(data_key="location")

    # ccmm 0..n; one funding_reference with multiple funders becomes multiple
    # RDM funding entries (one per funder, sharing the award)
    funding = SplitNested(FundingReferenceSchema, split_on="funder", data_key="funding_reference")

    # ccmm 0..n; ccmm-shaped in the model, no RDM counterpart (files are uploaded via the files API,
    # the distribution only describes them). Downloadable files of this server are not loaded,
    # see DistributionsField
    distributions = DistributionsField(data_key="distribution")

    # ccmm 0..n
    related_resources = fields.Nested(RelatedResourceSchema, many=True, data_key="related_resource")

    # ccmm 1..n; the metadata records of the source (a harvested dataset), stored as they came.
    # Dumped by DatasetSchema (without changes, or made from the record when there are none)
    metadata_identifications = fields.Nested(
        MetadataRecordSchema, many=True, data_key="metadata_identification", load_only=True
    )

    @post_load
    def use_created_date(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Use the date of the "Created" time reference as the publication date, if there is one."""
        created = next(
            (date["date"] for date in data.get("dates", []) if date.get("type", {}).get("id") == "created"), None
        )
        if created:
            # publication_date is a date or a date interval, the time of day is dropped
            data["publication_date"] = created if "/" in created else created.split("T")[0]
        return data

    @pre_load
    def merge_languages(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Prepend ccmm primary_language to other_language, both go to invenio languages."""
        if "primary_language" not in data:
            return data
        data = dict(data)
        data["other_language"] = [data.pop("primary_language"), *data.get("other_language", [])]
        return data

    def load_publication_year(self, value: Any) -> str:
        """Convert ccmm publication_year (gYear) to the first day of the year."""
        # ponytail: gYear may carry a timezone ("2025Z") - only the four-digit year is used
        year = str(value)[:4]
        if not year.isdigit():
            raise ValidationError(f"Invalid publication year: {value}")
        return f"{year}-01-01"

    def dump_publication_year(self, obj: dict[str, Any]) -> str | None:
        """Extract the year from invenio publication_date (EDTF: 2025, 2025-05, 2025-05-01, 2025/2026)."""
        publication_date = obj.get("publication_date")
        return publication_date[:4] if publication_date else None

    @post_dump(pass_original=True)
    def add_main_description(self, data: dict[str, Any], original: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Export the main RDM description as a description of type "other" (it has no ccmm counterpart).

        Goes first (it is the primary description). Records imported from ccmm keep the main description
        empty (their descriptions are the additional ones), so nothing is doubled for them.
        """
        if description := original.get("description"):
            dumped = DescriptionSchema().dump({"description": description, "type": {"id": "other"}})
            data["description"] = [dumped, *data.get("description", [])]
        return data

    @post_dump
    def split_languages(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Split invenio languages back to ccmm primary_language (the first one) and other_language."""
        # invenio does not know which language is primary - the first one is used,
        # so a ccmm record without primary_language gets one after a round trip
        if languages := data.pop("other_language", None):
            data["primary_language"], *other_languages = languages
            if other_languages:
                data["other_language"] = other_languages
        return data


class DatasetSchema(Schema):
    """ccmm dataset (generic json from convert_xml_to_json) <-> invenio record.

    The ccmm elements at the top level of the generic json become the record "metadata"
    (DatasetMetadataSchema), "ccmm_xml" (the source xml) is kept as-is on the record.

    terms_of_use/access_rights is not metadata in RDM, it is the record "access"
    (and "files" for metadata-only access), see access.py.
    """

    class Meta:
        """Schema options."""

        unknown = EXCLUDE

    metadata = fields.Nested(DatasetMetadataSchema)
    ccmm_xml = fields.String()

    # ccmm 1..n; loaded to metadata.metadata_identifications (DatasetMetadataSchema). Dumped from
    # there without changes (a harvested dataset), otherwise made from the technical metadata of
    # the record (a dataset created here), see metadata_record.py
    metadata_identification = fields.Function(metadata_records, dump_only=True)

    # ccmm terms_of_use/access_rights 1..1, moved to the top level and back (see wrap_metadata,
    # flatten_metadata); converted to the record access on load and from it on dump
    access_rights = CCMMVocabularyField("accessrights")

    @pre_load
    def wrap_metadata(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Wrap the top-level ccmm elements of the generic json as metadata, take out the access rights."""
        terms_of_use = data.get("terms_of_use")
        wrapped: dict[str, Any] = {"metadata": data}
        if isinstance(terms_of_use, dict) and "access_rights" in terms_of_use:
            wrapped["access_rights"] = terms_of_use["access_rights"]
            data = {**data, "terms_of_use": {k: v for k, v in terms_of_use.items() if k != "access_rights"}}
            wrapped["metadata"] = data
        if "ccmm_xml" in data:
            wrapped["ccmm_xml"] = data["ccmm_xml"]
        return wrapped

    @post_load
    def load_access(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Convert the access rights to the record access (and files, for metadata-only access)."""
        if not (access_rights := data.pop("access_rights", None)):
            return data
        access, files = rdm_access(access_rights["id"], (data.get("metadata") or {}).get("dates", []))
        data["access"] = access
        if files is not None:
            data["files"] = files
        return data

    @pre_dump
    def dump_access(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Convert the record access to the access rights."""
        if not data.get("access"):
            return data
        return {**data, "access_rights": {"id": access_right(data["access"], data.get("files"))}}

    @post_dump
    def flatten_metadata(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Merge the dumped metadata back to the top level, next to ccmm_xml; access rights to terms_of_use."""
        access_rights = data.pop("access_rights", None)
        data = {**data.pop("metadata", {}), **data}
        if access_rights:
            data["terms_of_use"] = {"access_rights": access_rights, **(data.get("terms_of_use") or {})}
        return data

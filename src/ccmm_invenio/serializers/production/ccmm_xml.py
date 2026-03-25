#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""CCMM XML serializer for CCMM production records."""

from __future__ import annotations

from typing import Any

from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import BaseSerializerSchema, SimpleSerializer
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]
from marshmallow import fields

YEAR_LENGTH = 4

CCMM_NS = "https://schema.ccmm.cz/research-data/1.1"
XML_NS = "http://www.w3.org/XML/1998/namespace"

NSMAP = {
    "ccmm": CCMM_NS,
    "xml": XML_NS,
}

LANGUAGE_IRI = "http://publications.europa.eu/resource/authority/language/"


class CCMMProductionXMLSerializer_1_1_0(MarshmallowSerializer):  # noqa: N801
    """Serializer CCMM XML."""

    def __init__(self, **options: Any):
        """Construct serializer."""
        super().__init__(
            format_serializer_cls=SimpleSerializer,
            object_schema_cls=CCMMXMLSchema,
            list_schema_cls=BaseListSchema,
            schema_kwargs={},
            encoder=self._to_xml_string,
            **options,
        )

    def _to_xml_string(self, data: dict, **kwargs: Any) -> Any:
        """Convert serialized data dictionary to XML string."""
        _ = kwargs
        root = self.build_xml(data)

        return etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        ).decode("utf-8")

    def build_xml(self, data: dict) -> etree._Element:
        """Build CCMM XML tree from serialized data."""
        root = etree.Element("dataset", nsmap=NSMAP)

        # title
        title = data.get("title")
        if title:
            title_el = etree.SubElement(root, "title")
            title_el.text = title

        # creators
        for creator in data.get("creators", []):
            qr_el = etree.SubElement(root, "qualified_relation")

            relation_el = etree.SubElement(qr_el, "relation")

            creator_type = creator.get("type")
            if creator_type == "organizational":
                agent_el = etree.SubElement(relation_el, "organization")
                self._append_organization(agent_el, creator)
            else:
                agent_el = etree.SubElement(relation_el, "person")
                self._append_person(agent_el, creator)

            role_el = etree.SubElement(qr_el, "role")
            role_id = creator.get("role_id")
            if role_id:
                iri_el = etree.SubElement(role_el, "iri")
                iri_el.text = role_id

        # publication_year
        publication_year = data.get("publication_year")
        if publication_year:
            pub_el = etree.SubElement(root, "publication_year")
            pub_el.text = publication_year

        # languages
        primary_language = data.get("primary_language")
        if primary_language:
            root.append(self._build_language_element("primary_language", primary_language))

        for language in data.get("other_languages", []):
            root.append(self._build_language_element("other_language", language))

        # dates
        for date_obj in data.get("dates", []):
            time_ref_el = etree.SubElement(root, "time_reference")
            self._append_time_reference(time_ref_el, date_obj)

        return root

    def _append_person(self, parent: etree._Element, creator: dict) -> None:
        """Append person element with names and affiliations."""
        name = creator.get("name")
        if name:
            name_el = etree.SubElement(parent, "name")
            name_el.text = name

        given_name = creator.get("given_name")
        if given_name:
            gn_el = etree.SubElement(parent, "given_name")
            gn_el.text = given_name

        family_name = creator.get("family_name")
        if family_name:
            fn_el = etree.SubElement(parent, "family_name")
            fn_el.text = family_name

        for aff_name in creator.get("affiliations", []):
            aff_el = etree.SubElement(parent, "affiliation")
            org_el = etree.SubElement(aff_el, "organization")
            org_name_el = etree.SubElement(org_el, "name")
            org_name_el.text = aff_name

    def _append_organization(self, parent: etree._Element, creator: dict) -> None:
        """Append organization element with name."""
        name = creator.get("name")
        if name:
            name_el = etree.SubElement(parent, "name")
            name_el.text = name

    def _build_language_element(self, element_name: str, language: str) -> etree._Element:
        """Build language element with IRI and labels."""
        lang_el = etree.Element(f"{element_name}")

        iri = language
        if iri:
            iri_el = etree.SubElement(lang_el, "iri")
            iri_el.text = iri

        return lang_el

    def _append_time_reference(self, parent: etree._Element, date_obj: dict) -> None:
        """Append time reference element with date and metadata."""
        temporal_representation_el = etree.SubElement(parent, "temporal_representation")

        date_value = date_obj.get("date")
        if date_value:
            if self._looks_like_year(date_value):
                time_instant_el = etree.SubElement(temporal_representation_el, "time_instant")
                year_as_date = f"{date_value}-01-01"
                date_el = etree.SubElement(time_instant_el, "date")
                date_el.text = year_as_date
            else:
                time_instant_el = etree.SubElement(temporal_representation_el, "time_instant")
                date_el = etree.SubElement(time_instant_el, "date")
                date_el.text = date_value

        date_type_el = etree.SubElement(parent, "date_type")
        type_iri = date_obj.get("type_id")
        if type_iri:
            iri_el = etree.SubElement(date_type_el, "iri")
            iri_el.text = type_iri

        date_information = date_obj.get("description")
        if date_information:
            info_el = etree.SubElement(parent, "date_information")
            info_el.text = date_information
            info_el.set(f"{{{XML_NS}}}lang", "en")

    def _looks_like_year(self, value: str) -> bool:
        """Return True if value looks like YYYY."""
        return len(value) == YEAR_LENGTH and value.isdigit()


class CCMMXMLSchema(BaseSerializerSchema):
    """Schema for extracting CCMM XML-relevant data from record."""

    title = fields.Method("get_title")
    creators = fields.Method("get_creators")
    publication_year = fields.Method("get_publication_year")
    primary_language = fields.Method("get_primary_language")
    other_languages = fields.Method("get_other_languages")
    dates = fields.Method("get_dates")

    def get_title(self, obj: dict) -> str:
        """Extract title from record metadata."""
        metadata = obj.get("metadata", {})
        return str(metadata.get("title"))

    def get_creators(self, obj: dict) -> list:
        """Extract creators list from record metadata."""
        metadata = obj.get("metadata", {})
        creators = metadata.get("creators", [])
        result = []

        for creator in creators:
            person_or_org = creator.get("person_or_org", {})
            if not person_or_org.get("name"):
                continue

            result.append(
                {
                    "name": person_or_org.get("name"),
                    "type": person_or_org.get("type"),
                    "given_name": person_or_org.get("given_name"),  # if no given name etc., it will be handled later
                    "family_name": person_or_org.get("family_name"),
                    "role_id": creator.get("role", {}).get("id"),
                    "affiliations": [aff.get("name") for aff in creator.get("affiliations", []) if aff.get("name")],
                }
            )

        return result

    def get_publication_year(self, obj: dict) -> str | None:
        """Extract publication year from publication date."""
        metadata = obj.get("metadata", {})
        publication_date = metadata.get("publication_date")
        if not publication_date:
            return None
        return str(publication_date)[:4]

    def get_primary_language(self, obj: dict) -> Any:
        """Extract and map primary language from metadata."""
        metadata = obj.get("metadata", {})
        languages = metadata.get("languages", [])
        if not languages:
            return None

        lang_id = languages[0].get("id")  # TODO: primary language == first language?
        if not lang_id:
            return None

        return self._get_language_iri(lang_id)

    def get_other_languages(self, obj: dict) -> list:
        """Extract and map additional languages from metadata."""
        metadata = obj.get("metadata", {})
        languages = metadata.get("languages", [])
        result = []

        for lang in languages[1:]:
            lang_id = lang.get("id")
            if not lang_id:
                continue
            result.append(self._get_language_iri(lang_id))

        return result

    def get_dates(self, obj: dict) -> list:
        """Extract date entries with type and description."""
        metadata = obj.get("metadata", {})
        dates = metadata.get("dates", [])
        result = []

        for date_obj in dates:
            value = date_obj.get("date")
            if not value:
                continue

            result.append(
                {
                    "date": value,
                    "type_id": date_obj.get("type", {}).get("id"),
                    "description": date_obj.get("description"),
                }
            )

        return result

    def _get_language_iri(self, lang_id: str) -> str:
        """Map language ID to iri entry."""
        return str(LANGUAGE_IRI + lang_id)

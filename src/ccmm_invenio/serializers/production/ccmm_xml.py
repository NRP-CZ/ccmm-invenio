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
from lxml import etree as ET
from marshmallow import fields

CCMM_NS = "https://schema.ccmm.cz/research-data/1.1"
XML_NS = "http://www.w3.org/XML/1998/namespace"

NSMAP = {
    "ccmm": CCMM_NS,
    "xml": XML_NS,
}


class CCMMProductionXMLSerializer_1_1_0(MarshmallowSerializer):  # noqa: N801
    """Serializer CCMM XML."""

    def __init__(self, **options: Any):
        super().__init__(
            format_serializer_cls=SimpleSerializer,
            object_schema_cls=CCMMXMLSchema,
            list_schema_cls=BaseListSchema,
            schema_kwargs={},
            encoder=self._to_xml_string,
            **options,
        )

    def _to_xml_string(self, data: dict, **kwargs: Any) -> str:
        """Build XML string from already serialized dict."""
        _ = kwargs
        root = self.build_xml(data)

        return ET.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        ).decode("utf-8")

    def build_xml(self, data: dict) -> ET._Element:
        """Build CCMM XML."""
        root = ET.Element(f"{{{CCMM_NS}}}dataset", nsmap=NSMAP)

        # title
        title = data.get("title")
        if title:
            title_el = ET.SubElement(root, f"{{{CCMM_NS}}}title")
            title_el.text = title

        # creators
        for creator in data.get("creators", []):
            qr_el = ET.SubElement(root, f"{{{CCMM_NS}}}qualified_relation")

            relation_el = ET.SubElement(qr_el, f"{{{CCMM_NS}}}relation")

            creator_type = creator.get("type")
            if creator_type == "organizational":
                agent_el = ET.SubElement(relation_el, f"{{{CCMM_NS}}}organization")
                self._append_organization(agent_el, creator)
            else:
                agent_el = ET.SubElement(relation_el, f"{{{CCMM_NS}}}person")
                self._append_person(agent_el, creator)

            role_el = ET.SubElement(qr_el, f"{{{CCMM_NS}}}role")
            role_id = creator.get("role_id")
            if role_id:
                iri_el = ET.SubElement(role_el, f"{{{CCMM_NS}}}iri")
                iri_el.text = role_id

        # publication_year
        publication_year = data.get("publication_year")
        if publication_year:
            pub_el = ET.SubElement(root, f"{{{CCMM_NS}}}publication_year")
            pub_el.text = publication_year

        # languages
        primary_language = data.get("primary_language")
        if primary_language:
            root.append(self._build_language_element("primary_language", primary_language))

        for language in data.get("other_languages", []):
            root.append(self._build_language_element("other_language", language))

        # dates
        for date_obj in data.get("dates", []):
            time_ref_el = ET.SubElement(root, f"{{{CCMM_NS}}}time_reference")
            self._append_time_reference(time_ref_el, date_obj)

        return root

    def _append_person(self, parent: ET._Element, creator: dict):
        """Append ccmm:person."""
        name = creator.get("name")
        if name:
            name_el = ET.SubElement(parent, f"{{{CCMM_NS}}}name")
            name_el.text = name

        given_name = creator.get("given_name")
        if given_name:
            gn_el = ET.SubElement(parent, f"{{{CCMM_NS}}}given_name")
            gn_el.text = given_name

        family_name = creator.get("family_name")
        if family_name:
            fn_el = ET.SubElement(parent, f"{{{CCMM_NS}}}family_name")
            fn_el.text = family_name

        for aff_name in creator.get("affiliations", []):
            aff_el = ET.SubElement(parent, f"{{{CCMM_NS}}}affiliation")
            org_el = ET.SubElement(aff_el, f"{{{CCMM_NS}}}organization")
            org_name_el = ET.SubElement(org_el, f"{{{CCMM_NS}}}name")
            org_name_el.text = aff_name

    def _append_organization(self, parent: ET._Element, creator: dict):
        """Append ccmm:organization."""
        name = creator.get("name")
        if name:
            name_el = ET.SubElement(parent, f"{{{CCMM_NS}}}name")
            name_el.text = name

    def _build_language_element(self, element_name: str, language: dict) -> ET._Element:
        """Build primary_language / other_language element."""
        lang_el = ET.Element(f"{{{CCMM_NS}}}{element_name}")

        iri = language.get("iri")
        if iri:
            iri_el = ET.SubElement(lang_el, f"{{{CCMM_NS}}}iri")
            iri_el.text = iri

        for label in language.get("labels", []):
            label_el = ET.SubElement(lang_el, f"{{{CCMM_NS}}}label")
            label_el.text = label["value"]
            label_el.set(f"{{{XML_NS}}}lang", label["lang"])

        return lang_el

    def _append_time_reference(self, parent: ET._Element, date_obj: dict):
        """Append ccmm:time_reference."""
        temporal_representation_el = ET.SubElement(parent, f"{{{CCMM_NS}}}temporal_representation")

        date_value = date_obj.get("date")
        if date_value:
            if self._looks_like_year(date_value):
                time_instant_el = ET.SubElement(temporal_representation_el, f"{{{CCMM_NS}}}time_instant")
                year_as_date = f"{date_value}-01-01"
                date_el = ET.SubElement(time_instant_el, f"{{{CCMM_NS}}}date")
                date_el.text = year_as_date
            else:
                time_instant_el = ET.SubElement(temporal_representation_el, f"{{{CCMM_NS}}}time_instant")
                date_el = ET.SubElement(time_instant_el, f"{{{CCMM_NS}}}date")
                date_el.text = date_value

        date_type_el = ET.SubElement(parent, f"{{{CCMM_NS}}}date_type")
        type_iri = date_obj.get("type_id")
        if type_iri:
            iri_el = ET.SubElement(date_type_el, f"{{{CCMM_NS}}}iri")
            iri_el.text = type_iri

        date_information = date_obj.get("description")
        if date_information:
            info_el = ET.SubElement(parent, f"{{{CCMM_NS}}}date_information")
            info_el.text = date_information
            info_el.set(f"{{{XML_NS}}}lang", "en")

    def _looks_like_year(self, value: str) -> bool:
        """Return True if value looks like YYYY."""
        return len(value) == 4 and value.isdigit()


LANGUAGE_VOCABULARY = {
    "CES": {
        "iri": "https://id.loc.gov/vocabulary/iso639-2/cze",
        "labels": [
            {"lang": "cs", "value": "čeština"},
            {"lang": "en", "value": "Czech"},
        ],
    },
    "ENG": {
        "iri": "https://id.loc.gov/vocabulary/iso639-2/eng",
        "labels": [
            {"lang": "cs", "value": "angličtina"},
            {"lang": "en", "value": "English"},
        ],
    },
}


class CCMMXMLSchema(BaseSerializerSchema):
    """Schema for extracting CCMM XML-relevant data from record."""

    title = fields.Method("get_title")
    creators = fields.Method("get_creators")
    publication_year = fields.Method("get_publication_year")
    primary_language = fields.Method("get_primary_language")
    other_languages = fields.Method("get_other_languages")
    dates = fields.Method("get_dates")

    def get_title(self, obj):
        metadata = obj.get("metadata", {})
        return metadata.get("title")

    def get_creators(self, obj):
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
                    "given_name": person_or_org.get("given_name"),
                    "family_name": person_or_org.get("family_name"),
                    "role_id": creator.get("role", {}).get("id"),
                    "affiliations": [aff.get("name") for aff in creator.get("affiliations", []) if aff.get("name")],
                }
            )

        return result

    def get_publication_year(self, obj):
        metadata = obj.get("metadata", {})
        publication_date = metadata.get("publication_date")
        if not publication_date:
            return None
        return str(publication_date)[:4]

    def get_primary_language(self, obj):
        metadata = obj.get("metadata", {})
        languages = metadata.get("languages", [])
        if not languages:
            return None

        lang_id = languages[0].get("id")
        if not lang_id:
            return None

        return self._map_language(lang_id)

    def get_other_languages(self, obj):
        metadata = obj.get("metadata", {})
        languages = metadata.get("languages", [])
        result = []

        for lang in languages[1:]:
            lang_id = lang.get("id")
            if not lang_id:
                continue
            result.append(self._map_language(lang_id))

        return result

    def get_dates(self, obj):
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

    def _map_language(self, lang_id: str) -> dict:
        return LANGUAGE_VOCABULARY.get(
            lang_id,
            {
                "iri": lang_id,
                "labels": [
                    {"lang": "en", "value": lang_id},
                ],
            },
        )

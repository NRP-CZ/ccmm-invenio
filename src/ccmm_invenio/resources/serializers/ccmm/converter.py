#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Conversion of CCMM XML to a generic JSON representation."""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import xmlschema
from xmlschema import ElementData, XMLSchemaConverter
from xmlschema.names import XSI_NAMESPACE
from xmlschema.utils.qnames import get_namespace

if TYPE_CHECKING:
    from collections.abc import Container

    from xmlschema import XMLSchemaBase, XMLSchemaValidationError
    from xmlschema.aliases import BaseXsdType, ElementType, NsmapType
    from xmlschema.validators import XsdElement

NS_CCMM_1_1_0 = "https://schema.ccmm.cz/research-data/1.1"
NS_GML = "http://www.opengis.net/gml/3.2"
CCMM_XML_MIMETYPE = "application/vnd.ccmm.research-data+xml"
# the default namespace is the one whose names are just local names in the json (see map_qname),
# the prefixes are used when serializing xml
NAMESPACES = {
    "": NS_CCMM_1_1_0,
    "gml": NS_GML,
    "xlink": "http://www.w3.org/1999/xlink",
    "xsi": XSI_NAMESPACE,
}
RENAME = {
    "{http://www.w3.org/XML/1998/namespace}lang": "lang",
}

UNRENAME = {v: k for k, v in RENAME.items()}


def _is_gml(xsd_element: XsdElement | None, xsd_type: BaseXsdType | None) -> bool:
    """Return True for gml elements (gml:MultiSurface, ...) and ccmm elements of gml type (bounding_box)."""
    return NS_GML in (
        xsd_element.target_namespace if xsd_element else None,
        xsd_type.target_namespace if xsd_type else None,
    )


class XMLToGenericJSONConverter(XMLSchemaConverter):
    """Custom converter that is able to convert XML to generic JSON and vice versa.

    It cooperates with an xml schema to do a schema-aware mapping of arrays and datatypes.
    GML content (geometries, bounding boxes) is not converted, it is kept as a serialized xml string.

    Use xml_to_json and json_to_xml, they set up the hooks and options the conversion needs.
    """

    def __init__(
        self,
        namespaces: NsmapType | None = None,
        attr_prefix: str | None = "",  # no attribute/element name conflicts, see test_no_attribute_element_conflicts
        text_key: str | None = "$",
        **kwargs: Any,
    ):
        """Create the converter, defaulting to the generic json options."""
        super().__init__(
            namespaces=NAMESPACES if namespaces is None else namespaces,
            attr_prefix=attr_prefix,
            text_key=text_key,
            **kwargs,
        )
        # see _push_source_element
        self._source_elements: list[ElementType] = []

    def xml_to_json(self, schema: XMLSchemaBase, xml_data: str) -> tuple[Any, list[XMLSchemaValidationError]]:
        """Convert an XML document, passed as a string, to generic JSON.

        :return: the converted data and a list of validation errors (empty if the document is valid).
        """
        return cast(
            "tuple[Any, list[XMLSchemaValidationError]]",
            schema.to_dict(
                xml_data,
                converter=self,
                validation_hook=self._push_source_element,
                element_hook=self._serialize_gml,
                validation="lax",
            ),
        )

    def json_to_xml(
        self, schema: XMLSchemaBase, data: dict[str, Any], root: str
    ) -> tuple[str, list[XMLSchemaValidationError]]:
        """Convert generic JSON (as returned by xml_to_json) back to an XML document with the given root element.

        :return: the serialized xml and a list of validation errors (empty if the document is valid).
        """
        data = {k: v for k, v in data.items() if k != "ccmm_xml"}  # ccmm_xml is the xml itself, not an element
        elem, errors = cast(
            "tuple[ElementType, list[XMLSchemaValidationError]]",
            schema.encode(
                data,
                path=root,
                converter=self,
                validation="lax",
                use_defaults=False,  # do not add attributes that are not in the json
                # the order of the json keys (e.g. from marshmallow dump) is not the order of the xsd sequences
                unordered=True,
            ),
        )
        return cast("str", xmlschema.etree_tostring(elem, namespaces=self.namespaces)), errors

    # validation_hook is called before an element is decoded, element_hook after it,
    # so a stack pairs the decoded data with its source element.
    def _push_source_element(self, elem: ElementType, _xsd_element: XsdElement) -> bool:
        self._source_elements.append(elem)
        return False  # continue with validation and decoding

    def _serialize_gml(
        self, data: ElementData, xsd_element: XsdElement | None, xsd_type: BaseXsdType | None
    ) -> ElementData:
        elem = self._source_elements.pop()
        # the outermost gml element is serialized with all its children, nested ones are skipped
        if _is_gml(xsd_element, xsd_type) and not (
            self._source_elements and get_namespace(self._source_elements[-1].tag) == NS_GML
        ):
            return ElementData(
                data.tag, xmlschema.etree_tostring(elem, namespaces=self.namespaces), None, None, data.xmlns
            )
        return data

    def map_qname(self, qname: str) -> str:
        """Map a QName to a json name.

        Uses the RENAME mapping if available. Names in the default (ccmm) namespace or in no namespace
        (unqualified attributes) become the local name, others stay as "{namespace}local" - independent
        of the prefixes used in the xml. unmap_qname of the superclass maps both forms back.
        """
        if qname in RENAME:
            return RENAME[qname]
        if get_namespace(qname) in ("", self.default_namespace):
            return qname.rpartition("}")[2]  # "{namespace}local" or "local"
        return qname

    def unmap_qname(
        self,
        qname: str,
        name_table: Container[str | None] | None = None,
        xmlns: list[tuple[str, str]] | None = None,
    ) -> str:
        """Map a string back to a QName, using the UNRENAME mapping if available, otherwise delegates to superclass."""
        return UNRENAME.get(qname) or super().unmap_qname(qname, name_table, xmlns)

    def element_encode(self, obj: Any, xsd_element: XsdElement, level: int = 0) -> ElementData:
        """Encode an element, parsing gml kept as a serialized xml string first."""
        if isinstance(obj, str) and _is_gml(xsd_element, xsd_element.type):
            # validation is skipped here, the whole document is validated during encoding;
            # no defaults so that the element is encoded exactly as it was serialized
            obj = xsd_element.decode(
                xmlschema.XMLResource(obj).root,
                converter=type(self)(),
                validation="skip",
                use_defaults=False,
            )
        if not isinstance(obj, MutableMapping):
            return super().element_encode(obj, xsd_element, level)

        # with an empty attr_prefix, the superclass encodes single-valued attributes as child elements,
        # so pick the attributes here. Safe as there are no attribute/element name conflicts.
        obj = dict(obj)
        attributes = {}
        for name in list(obj):
            if self.is_xmlns(name):
                continue
            qname = self.unmap_qname(name, xsd_element.attributes)
            if qname in xsd_element.attributes or get_namespace(qname) == XSI_NAMESPACE:
                attributes[qname] = obj.pop(name)
        data = super().element_encode(obj, xsd_element, level)
        return data._replace(attributes={**(data.attributes or {}), **attributes})


ccmm_1_1_0_schema = xmlschema.XMLSchema11(Path(__file__).parent / "xsd" / "ccmm-1.1.0-2026-01-29.xsd")


def convert_xml_to_json(xml_data: str) -> tuple[Any, list[XMLSchemaValidationError]]:
    """Convert a CCMM 1.1.0 XML document, passed as a string, to generic JSON.

    The source xml is kept as the "ccmm_xml" field of the returned json.
    """
    data, errors = XMLToGenericJSONConverter().xml_to_json(ccmm_1_1_0_schema, xml_data)
    if isinstance(data, dict):
        data["ccmm_xml"] = xml_data
    return data, errors


def convert_json_to_xml(data: dict[str, Any]) -> tuple[str, list[XMLSchemaValidationError]]:
    """Convert generic JSON (as returned by convert_xml_to_json) back to a CCMM 1.1.0 XML document."""
    return XMLToGenericJSONConverter().json_to_xml(ccmm_1_1_0_schema, data, f"{{{NS_CCMM_1_1_0}}}dataset")

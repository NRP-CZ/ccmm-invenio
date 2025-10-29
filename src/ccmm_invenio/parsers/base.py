#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Base classes and protocols for CCMM XML Invenio parsers."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from functools import partial, wraps
from typing import Any, Literal, Protocol, cast, overload

from lxml.etree import QName, tostring
from lxml.etree import _Element as Element


class ParseError(Exception):
    """Exception raised for errors during parsing."""


class VocabularyLoader(Protocol):
    """Protocol for a vocabulary loader callable."""

    def __call__(self, vocabulary_type: str, iri: str) -> str:
        """Protocol for a vocabulary loader callable.

        Resolve the given IRI to its internal invenio identifier based on the vocabulary type.
        Raises KeyError if the IRI is not found.
        """
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class QualifiedTag:
    """Helper class for qualified XML tag names.

    from encodings.cp857 import StreamWriter
    A QualifiedTag represents an XML element or attribute with its namespace URI and local name.
    They can be hashed and used as dictionary keys. The `get_all_children` and `get_single_child` methods
    help to find child elements with the given tag in an lxml Element.
    """

    namespace: str
    tag: str

    def __str__(self) -> str:
        """Return the fully qualified name for the XML element or attribute."""
        return f"{{{self.namespace}}}{self.tag}"

    def __repr__(self) -> str:
        """Return the string representation of the QualifiedTag."""
        return f"{{{self.namespace}}}{self.tag}"

    def get_all_children(self, parent: Element) -> list[Element]:
        """Get all child elements with this tag from the given parent element."""
        matching_children = []
        for child in parent.iterchildren():
            # if the child is not element, continue
            if not isinstance(child.tag, str):
                continue
            qname = QName(child)
            # Check if the tag's namespace URI and local name match
            if qname.namespace == self.namespace and qname.localname == self.tag:
                matching_children.append(child)
        return matching_children

    def get_single_child(self, parent: Element) -> Element | None:
        """Get a single child element with this tag from the given parent element."""
        children = self.get_all_children(parent)
        if len(children) == 1:
            return children[0]
        if len(children) > 1:
            raise ValueError(f"Expected single child with tag '{self}', found multiple in element '{parent.tag}'")
        return None

    @staticmethod
    def from_qname(qname: QName) -> QualifiedTag:
        """Create a QualifiedTag from an lxml QName."""
        return QualifiedTag(namespace=qname.namespace, tag=qname.localname)

    @staticmethod
    def from_element(el: Element) -> QualifiedTag:
        """Create a QualifiedTag from an lxml Element."""
        qname = QName(el)
        return QualifiedTag(namespace=qname.namespace, tag=qname.localname)


class XMLNamespace:
    """Helper class for XML namespace handling.

    This class allows easier creating of QualifiedTag instances for elements and attributes
    within a specific XML namespace.

    Example:
    ```
    ns = XMLNamespace(
        "http://example.com/ns"
    )
    title_tag = ns.title  # QualifiedTag for {http://example.com/ns}title
    attr_tag = ns.attribute  # QualifiedTag for {http://example.com/ns}attribute
    ```

    """

    def __init__(self, uri: str):
        """Initialize the XMLNamespace with the given URI."""
        self.uri = uri

    def __getattr__(self, name: str) -> QualifiedTag:
        """Get the fully qualified name for the given XML element or attribute name."""
        return QualifiedTag(namespace=self.uri, tag=name)

    def __getitem__(self, name: str) -> QualifiedTag:
        """Get the fully qualified name for the given XML element or attribute name."""
        return QualifiedTag(namespace=self.uri, tag=name)


class ParserFunction(Protocol):
    """Protocol for parser functions."""

    @overload
    def __call__(self, el: Element, path: list[QualifiedTag]) -> Any: ...

    @overload
    def __call__(self, el: Element, path: list[QualifiedTag], **kwargs: Any) -> Any: ...

    def __call__(self, el: Element, path: list[QualifiedTag], **kwargs: Any) -> Any:
        """Protocol for parser functions."""
        raise NotImplementedError


@dataclasses.dataclass(frozen=True, kw_only=True)
class VocabularyTag(QualifiedTag):
    """QualifiedTag subclass for vocabulary elements."""

    parser: CCMMXMLParser

    @overload
    def parse_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single"],
        **kwargs: Any,
    ) -> dict[str, str]: ...

    @overload
    def parse_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["optional"],
        **kwargs: Any,
    ) -> dict[str, str] | None: ...

    @overload
    def parse_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["array"],
        **kwargs: Any,
    ) -> list[dict[str, str]]: ...

    @overload
    def parse_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["optional_array"],
        **kwargs: Any,
    ) -> list[dict[str, str]]: ...

    def parse_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single", "optional", "array", "optional_array"] = "single",
        **kwargs: Any,
    ) -> Any:
        """Find a child element with the given tag and parse its content."""
        return self.parser.parse_field(
            tag,
            children,
            path,
            cardinality,
            datatype=self,
            **kwargs,
        )

    def parse_content(
        self,
        el: Element,
        path: list[QualifiedTag],
        **kwargs: Any,
    ) -> dict[str, str]:
        """Parse the content of a vocabulary element."""
        try:
            return cast(
                "dict[str, str]",
                self.parser.parse_content(
                    el,
                    path,
                    datatype=self,
                    **kwargs,
                ),
            )
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"Failed to parse content for {self.parser}: {tostring(el)}") from e


def raise_if_not_empty(*exceptions: QualifiedTag | str) -> Callable:
    """Raise an exception if the element is not empty."""

    def wrapper[T: Callable](f: T) -> T:
        """Wrap function to check for unexpected elements."""

        @wraps(f)
        def wrapped(self: CCMMXMLParser, el: Element, path: list[QualifiedTag], **kwargs: Any) -> Any:
            # Remove exceptions from the element before checking
            ret = f(self, el, path, **kwargs)
            namespaced_exceptions = {self.ns[exc] if isinstance(exc, str) else exc for exc in exceptions}
            for child in list(el.iterchildren()):
                if not isinstance(child.tag, str) or QualifiedTag.from_element(child) in namespaced_exceptions:
                    child.getparent().remove(child)

            if len(el):
                # serialize the element to string using lxml
                stringified_el = tostring(el, encoding="unicode")
                raise ValueError(f"Unexpected elements in path '{path}': {stringified_el}")
            return ret

        return wrapped  # type: ignore[return-value]

    return wrapper


def remove_empty[T: Callable](f: T) -> T:
    """Remove empty values from a dictionary."""

    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        """Call wrapped function and remove empty values from the resulting dictionary."""
        ret = f(*args, **kwargs)
        if isinstance(ret, dict):
            for k in list(ret.keys()):
                if (
                    ret[k] is None
                    or (isinstance(ret[k], dict) and not ret[k])
                    or (isinstance(ret[k], list) and not ret[k])
                ):
                    del ret[k]
            return ret
        if isinstance(ret, list):
            return [
                item
                for item in ret
                if not (item is None or (isinstance(item, dict) and not item) or (isinstance(item, list) and not item))
            ]
        return ret

    return wrapped  # type: ignore[return-value]


def datatype_parser(
    unparsed: list[QualifiedTag | str] | None = None,
    datatype: QualifiedTag | str | None = None,
) -> Callable:
    """Mark a specific function as being a parser.

    The signature of the function must match ParserFunction protocol
    with or without kwargs.

    If datatype is None, the function will be registered with ns.__name__.
    """

    def wrapper[T: Callable](f: T) -> T:
        """Wrap function to register it as a parser for the given datatype."""
        f = remove_empty(f)
        f = raise_if_not_empty(*(unparsed or []))(f)
        f.__datatype__ = datatype  # type: ignore[attr-defined]
        return f

    return wrapper


internal = XMLNamespace("http://cesnet.cz/ccmm/invenio/internal")


class CCMMXMLParser:
    """Parser for CCMM XML records."""

    ns: XMLNamespace
    vocabulary_ns = XMLNamespace("http://vocabs.ccmm.cz/registry/")
    gml = XMLNamespace("http://www.opengis.net/gml/3.2")

    text_datatype = internal.text
    i18ndict_datatype = internal.i18ndict

    def __init__(self, vocabulary_loader: VocabularyLoader):
        """Initialize the parser with the given vocabulary loader."""
        self.vocabulary_loader = vocabulary_loader
        self.parser_functions: dict[QualifiedTag, ParserFunction] = {
            self.text_datatype: self.parse_text_content,  # type: ignore[dict-item]
            self.i18ndict_datatype: self.parse_i18ndict_content,  # type: ignore[dict-item]
        }

        # iterate over all methods of the class and register those marked as datatype parsers
        for attr_name in dir(self):
            if not attr_name.startswith("parse_"):
                continue
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "__datatype__"):
                datatype = getattr(attr, "__datatype__", None)
                if datatype is None:
                    datatype = self.ns[attr_name[len("parse_") :]]
                elif isinstance(datatype, str):
                    datatype = self.ns[datatype]
                self.parser_functions[datatype] = cast(
                    "ParserFunction",
                    attr,
                )

    #
    # Public API
    #
    def parse(self, xml_root: Element) -> dict[str, Any]:
        """Parse the given CCMM XML root element into a dictionary."""
        raise NotImplementedError

    #
    # Helper methods to be used by subclasses
    #
    def children(self, el: Element) -> dict[QualifiedTag, list[Element]]:
        """Return a mapping of child QualifiedTags to their elements.

        This is an optimization to avoid repeated calls to iterchildren() with
        filtering on tag names. The returned dictionary maps QualifiedTag instances
        to lists of child elements with that tag, the child elements are in the same
        order as they appear in the XML.
        """
        children_map: dict[QualifiedTag, list[Element]] = {}
        for child in el.iterchildren():
            if not isinstance(child.tag, str):
                continue
            qtag = QualifiedTag.from_element(child)
            if qtag not in children_map:
                children_map[qtag] = []
            children_map[qtag].append(child)
        return children_map

    #
    # Parsers for individual data types. These are in two forms: content parsers and field parsers.
    # Content parsers parse the content of a received element, field parsers find the child element
    # with the given tag and call the content parser on it.
    #

    def parse_content(
        self,
        el: Element,
        path: list[QualifiedTag],
        datatype: QualifiedTag | str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Parse the content of a received element using the provided parse function."""
        dt: QualifiedTag
        if not datatype:
            dt = QualifiedTag.from_element(el)
        elif isinstance(datatype, str):
            dt = self.ns[datatype]
        else:
            dt = datatype

        parser_func = self.parser_functions.get(dt)
        if not parser_func:
            raise ValueError(f"No parser function registered for datatype '{dt}' at path '{path}'")
        try:
            return parser_func(el, path, **kwargs)
        except ParseError:
            raise
        except Exception as e:
            # pytest does not show correct traceback in chained exceptions
            # so we add with_traceback here
            raise ParseError(
                f"Failed to parse content for {getattr(parser_func, '__name__', parser_func)}: {e}\n"
                f"{tostring(el, encoding='unicode', pretty_print=True)}"
            ).with_traceback(e.__traceback__) from e

    def parse_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single", "optional", "array", "optional_array"] = "single",
        datatype: QualifiedTag | str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Find a child element with the given tag and parse its content."""
        selected_children = children.get(tag, [])
        for child_el in selected_children:
            child_el.getparent().remove(child_el)

        if cardinality == "single":
            return self._parse_single_required_child(selected_children, tag, path, datatype, **kwargs)
        if cardinality == "optional":
            return self._parse_single_optional_child(selected_children, tag, path, datatype, **kwargs)
        if cardinality in ("array", "optional_array"):
            ret = [
                self.parse_content(child_el, [*path, tag], datatype=datatype, **kwargs)
                for child_el in selected_children
            ]
            if cardinality == "array" and not ret:
                raise ValueError(f"Missing required child elements '{tag}' at path '{path}'")
            return ret
        raise ValueError(f"Unknown cardinality '{cardinality}' for tag '{tag}'")

    def _parse_single_required_child(
        self,
        selected_children: list[Element],
        tag: QualifiedTag,
        path: list[QualifiedTag],
        datatype: QualifiedTag | str | None,
        **kwargs: Any,
    ) -> Any:
        if not selected_children:
            raise ValueError(f"Missing required child element '{tag}' at path '{path}'")
        if len(selected_children) > 1:
            raise ValueError(f"Multiple child elements '{tag}' found at path '{path}', expected single")
        ret = self.parse_content(selected_children[0], [*path, tag], datatype=datatype, **kwargs)
        if ret is None:
            raise ValueError(f"Child element '{tag}' at path '{path}' parsed to None, expected value")
        return ret

    def _parse_single_optional_child(
        self,
        selected_children: list[Element],
        tag: QualifiedTag,
        path: list[QualifiedTag],
        datatype: QualifiedTag | str | None,
        **kwargs: Any,
    ) -> Any:
        if not selected_children:
            return None
        if len(selected_children) > 1:
            raise ValueError(f"Multiple child elements '{tag}' found at path '{path}', expected single or none")
        return self.parse_content(selected_children[0], [*path, tag], datatype=datatype, **kwargs)

    #
    # Vocabulary parsers
    #

    def register_vocabulary_parser(
        self,
        vocabulary_type: str,
    ) -> VocabularyTag:
        """Register a parser for a vocabulary element of the given type.

        Called in constructor to set up the parser functions.

        Example:
            self.title_type = self.register_vocabulary_parser("titletypes")

        Later on:
            title_type = self.parse_field(
                self.ns.title_type,
                children,
                path,
                cardinality="optional",
                datatype=self.title_type,
            )
        or simply:
            title_type = self.title_type.parse_field(
                self.ns.title_type,
                children,
                path,
                cardinality="optional",
            )
        or to parse content:
            title_type = self.title_type.parse_content(
                el,
                path,
            )

        """
        tag = VocabularyTag(namespace=self.vocabulary_ns.uri, tag=vocabulary_type, parser=self)
        self.parser_functions[tag] = partial(
            self.parse_vocabulary_content,
            vocabulary_type=vocabulary_type,
        )
        return tag

    def parse_vocabulary_content(
        self,
        el: Element,
        path: list[QualifiedTag],
        *,
        vocabulary_type: str,
        **kwargs: Any,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Parse the content of a vocabulary element."""
        # Parse IRI (required for vocabulary items)
        children = self.children(el)
        iri_value = self.parse_text_field(self.ns.iri, children, path, cardinality="single")

        return {"id": self.vocabulary_loader(vocabulary_type, iri_value)}

    #
    # Text parsers
    #
    def parse_text_content(
        self,
        el: Element,
        path: list[QualifiedTag],  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> str:
        """Parse a simple text element."""
        text: str | None = el.text
        if text is None:
            return ""
        # Remove any leading/trailing whitespace
        return text.strip()

    @overload
    def parse_text_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single"],
        **kwargs: Any,
    ) -> str: ...

    @overload
    def parse_text_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["optional"],
        **kwargs: Any,
    ) -> str | None: ...

    @overload
    def parse_text_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["array"],
        **kwargs: Any,
    ) -> list[str]: ...

    @overload
    def parse_text_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["optional_array"],
        **kwargs: Any,
    ) -> list[str]: ...

    def parse_text_field(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single", "optional", "array", "optional_array"] = "single",
        **kwargs: Any,
    ) -> str | None | list[str]:
        """Parse a simple text element."""
        return cast(
            "str | None | list[str]",
            self.parse_field(
                tag,
                children,
                path,
                cardinality,
                datatype=self.text_datatype,
                **kwargs,
            ),
        )

    def parse_i18ndict_content(
        self,
        el: Element,
        path: list[QualifiedTag],
    ) -> dict[str, str]:
        """Parse a multilingual text element with xml:lang attributes.

        return language code -> text
        """
        lang = el.get("{http://www.w3.org/XML/1998/namespace}lang")
        if not lang:
            lang = "und"  # Undetermined language code
        return {
            lang: self.parse_text_content(el, path),
        }

    def parse_i18ndict(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single", "optional"] = "single",
    ) -> dict[str, str]:
        """Parse a multilingual text element with xml:lang attributes.

        return language code -> text
        """
        ret = self.parse_field(
            tag,
            children,
            path,
            cardinality="array",
            datatype=self.i18ndict_datatype,
        )
        i18ndict: dict[str, str] = {}
        for item in ret:
            i18ndict.update(item)
        if cardinality == "single" and not i18ndict:
            raise ValueError(f"Missing required multilingual field '{tag}' at path '{path}'")
        return i18ndict

    def parse_multilingual(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single", "optional"] = "single",
    ) -> list[dict[str, str]]:
        """Parse a multilingual text element with xml:lang attributes."""
        ret = self.parse_field(
            tag,
            children,
            path,
            cardinality="array" if cardinality == "single" else "optional_array",
            datatype=self.i18ndict_datatype,
        )
        multilingual_list: list[dict[str, str]] = []
        for item in ret:
            for k, v in item.items():
                multilingual_list.append({"lang": k, "value": v})
        if cardinality == "single" and not multilingual_list:
            raise ValueError(f"Missing required multilingual field '{tag}' at path '{path}'")
        return multilingual_list

    def parse_i18n(
        self,
        tag: QualifiedTag,
        children: dict[QualifiedTag, list[Element]],
        path: list[QualifiedTag],
        cardinality: Literal["single", "optional", "array", "optional_array"] = "single",
    ) -> list[dict[str, str]] | dict[str, str] | None:
        """Parse a i18nstr text element with xml:lang attributes."""
        ret = self.parse_field(
            tag,
            children,
            path,
            cardinality="array" if cardinality == "single" else "optional_array",
            datatype=self.i18ndict_datatype,
        )
        multilingual_list: list[dict[str, str]] = []
        for item in ret:
            for k, v in item.items():
                multilingual_list.append({"lang": k, "value": v})
        if cardinality in ("single", "optional"):
            if not multilingual_list:
                if cardinality == "single":
                    raise ValueError(f"Missing required i18n field '{tag}' at path '{path}'")
                return None
            if len(multilingual_list) > 1:
                raise ValueError(f"Multiple entries for single i18n field '{tag}' at path '{path}'")
            return multilingual_list[0]
        if cardinality == "array" and not multilingual_list:
            raise ValueError(f"Missing required i18n field '{tag}' at path '{path}'")
        return multilingual_list

    @datatype_parser()
    def parse_long(self, el: Element, path: list[QualifiedTag]) -> int:
        """Parse a long integer element."""
        text = self.parse_text_content(el, path)
        try:
            return int(text)
        except ValueError as e:
            raise ValueError(f"Failed to parse long integer at path '{path}': '{text}'") from e

    @datatype_parser()
    def parse_int(self, el: Element, path: list[QualifiedTag]) -> int:
        """Parse an integer element."""
        text = self.parse_text_content(el, path)
        try:
            return int(text)
        except ValueError as e:
            raise ValueError(f"Failed to parse integer at path '{path}': '{text}'") from e

    @datatype_parser()
    def parse_double(self, el: Element, path: list[QualifiedTag]) -> float:
        """Parse a double (floating point) element."""
        text = self.parse_text_content(el, path)
        try:
            return float(text)
        except ValueError as e:
            raise ValueError(f"Failed to parse double at path '{path}': '{text}'") from e

    @datatype_parser()
    def parse_date(self, el: Element, path: list[QualifiedTag]) -> str:
        """Parse a date element (ISO 8601 format)."""
        # No need to add validation as invenio will validate the date format later
        return self.parse_text_content(el, path)

    @datatype_parser()
    def parse_datetime(self, el: Element, path: list[QualifiedTag]) -> str:
        """Parse a datetime element (ISO 8601 format)."""
        # No need to add validation as invenio will validate the date format later
        return self.parse_text_content(el, path)

    @datatype_parser()
    def parse_gmlspaceseparateddoublelist(self, el: Element, path: list[QualifiedTag]) -> list[float]:
        """Parse a GML space-separated double list element."""
        text = self.parse_text_content(el, path)
        try:
            return [float(x) for x in text.split()]
        except ValueError as e:
            raise ValueError(f"Failed to parse GML space-separated double list at path '{path}': '{text}'") from e

    @datatype_parser()
    def parse_gmlenvelopetype(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type GMLEnvelopeType to GMLEnvelopeType."""
        children = self.children(el)
        return {
            "lowerCorner": self.parse_field(
                self.gml.lowerCorner,
                children,
                path,
                cardinality="single",
                datatype="gmlspaceseparateddoublelist",
            ),
            "upperCorner": self.parse_field(
                self.gml.upperCorner,
                children,
                path,
                cardinality="single",
                datatype="gmlspaceseparateddoublelist",
            ),
        }

    @datatype_parser()
    def parse_ccmmgeometry(self, el: Element, path: list[QualifiedTag]) -> dict[str, Any]:
        """Parse a CCMM geometry element."""
        children = self.children(el)
        ret = {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
            "wkt": self.parse_field(
                self.ns.wkt,
                children,
                path,
                cardinality="single",
                datatype="ccmmwkt",
            ),
        }
        # move the geometry substitution to a "geometry" key with serialized xml as a value
        # we suppose that all elements within the gml namespace are geometry elements
        gml_children = []
        for child in list(el.iterchildren()):
            if not isinstance(child.tag, str):
                continue
            qname = QName(child)
            if qname.namespace == "http://www.opengis.net/gml/3.2":
                child.getparent().remove(child)
                gml_children.append(child)
        if gml_children:
            if len(gml_children) > 1:
                raise ValueError(f"Multiple GML geometry elements found at path '{path}', expected single")
            ret["geometry"] = tostring(gml_children[0])
        return ret

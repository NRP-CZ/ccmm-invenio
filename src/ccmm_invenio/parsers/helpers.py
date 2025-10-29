#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Helper functions for XML parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lxml.etree import _Element as Element


def remove_empty_from_list(lst: list[Any]) -> None:
    """Remove empty values from a list."""
    lst[:] = [
        item
        for item in lst
        if item is not None and not (isinstance(item, dict) and not item) and not (isinstance(item, list) and not item)
    ]


def find_and_parse(parent: Element, tag: str, parse_func: Any, path: list[str]) -> Any | None:
    """Find and parse a child element."""
    child = parent.find(tag)
    if child is not None:
        result = parse_func(child, [*path, tag])
        parent.remove(child)
        return result
    return None


def find_and_parse_array(parent: Element, tag: str, parse_func: Any, path: list[str]) -> list[Any] | None:
    """Find and parse an array of child elements."""
    children = parent.findall(tag)
    results = []
    for child in children:
        result = parse_func(child, [*path, tag])
        parent.remove(child)
        results.append(result)
    return results if results else None

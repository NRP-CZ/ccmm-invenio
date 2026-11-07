# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Helpers of the resolver mappings building the record shape (moved here from oarepo-related-resources)."""

from __future__ import annotations

from typing import Any


def build_person_or_org(  # noqa: PLR0913
    *,
    name: str | None,
    type_: str = "personal",
    given: str | None = None,
    family: str | None = None,
    identifiers: list | None = None,
    affiliations: list | None = None,
) -> dict[str, Any]:
    """Build an RDM creator/contributor entry.

    Returns ``{"person_or_org": {...}}`` with optional ``"affiliations"``. Optional
    fields are omitted when falsy, matching Invenio RDM's tolerated shape.
    """
    person: dict[str, Any] = {"name": name, "type": type_}
    if given:
        person["given_name"] = given
    if family:
        person["family_name"] = family
    if identifiers:
        person["identifiers"] = identifiers
    entry: dict[str, Any] = {"person_or_org": person}
    if affiliations:
        entry["affiliations"] = affiliations
    return entry

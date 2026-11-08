# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Vocabulary records created from the ORCID and ROR identifiers of a record.

With ``CCMM_FETCH_IDENTIFIERS``, a record may refer to people, affiliations and funders that are
not in the vocabularies yet. The component downloads them before the record is committed, so that
the relations of the record are valid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import current_app
from invenio_records_resources.services.records.components import ServiceComponent
from oarepo_related_resources.services import resolve_orcid, resolve_ror

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from invenio_db.uow import UnitOfWork

IDENTIFIER_LOCATIONS = {
    "metadata.creators.person_or_org.identifiers": "names",
    "metadata.creators.affiliations": "affiliations",
    "metadata.contributors.person_or_org.identifiers": "names",
    "metadata.contributors.affiliations": "affiliations",
    "metadata.funding.funder": "funders",
    "metadata.metadata_identifications.qualified_relations.person_or_org.identifiers": "names",
    "metadata.metadata_identifications.qualified_relations.affiliations": "affiliations",
    # a related resource loaded by DOI keeps the ROR of its funders
    "metadata.related_resources.funding.funder": "funders",
    "metadata.related_resources.creators.affiliations": "affiliations",
    "metadata.related_resources.contributors.affiliations": "affiliations",
}
"""Where the identifiers are (a list on the way is walked through) and the vocabulary they belong to.

All the relations to affiliations and funders must be here, an unknown id fails the record otherwise.
The people of related resources are left out on purpose: names are not relations, so nothing fails
without them, and an article may have thousands of authors, each one looked up on every save.
"""

IDENTIFIER_RESOLVERS: dict[tuple[str, str | None], Callable] = {
    ("names", "orcid"): resolve_orcid,
    ("affiliations", "ror"): resolve_ror,
    ("affiliations", None): resolve_ror,
    ("funders", "ror"): resolve_ror,
    ("funders", None): resolve_ror,
}
"""The resolver of (vocabulary, identifier scheme); affiliations and funders have the ROR as their id."""


def lookup_with_arrays(data: Any, path: str) -> Iterator[tuple[Any, Any, str]]:
    """Yield (value, parent, full path) of every value at the dot-separated path, going through lists."""

    def lookup(value: Any, parts: list[str], walked: list[str], parent: Any) -> Iterator[tuple[Any, Any, str]]:
        if isinstance(value, list):
            for index, item in enumerate(value):
                yield from lookup(item, parts, [*walked, str(index)], parent)
        elif not parts:
            yield value, parent, ".".join(walked)
        elif isinstance(value, dict) and parts[0] in value:
            yield from lookup(value[parts[0]], parts[1:], [*walked, parts[0]], value)

    yield from lookup(data, path.split("."), [], None)


def resolve_identifier(  # noqa: PLR0913,PLR0917
    identifier: dict[str, Any],
    parent: Any,
    path: str,
    vocabulary: str,
    uow: UnitOfWork | None = None,
    session: Any = None,
) -> None:
    """Create the vocabulary record of a single identifier, if it has a resolver, and set its id."""
    id_key = "identifier" if "identifier" in identifier else "id"
    resolver = IDENTIFIER_RESOLVERS.get((vocabulary, identifier.get("scheme")))
    if id_key not in identifier or resolver is None:
        return
    resolved = resolver(
        identifier[id_key],
        vocabulary=vocabulary,
        parent=parent,
        create_vocabulary_record=True,
        check_existing=True,
        path=path,
        uow=uow,
        session=session,
    )
    identifier[id_key] = resolved["id"]


def resolve_identifiers(data: dict[str, Any], uow: UnitOfWork | None = None, session: Any = None) -> None:
    """Create the vocabulary records of all the identifiers in the record data.

    An identifier that can not be resolved is logged and left as it is: if it is a relation,
    the record then fails on it when it is committed.
    """
    for location, vocabulary in IDENTIFIER_LOCATIONS.items():
        for identifier, parent, path in lookup_with_arrays(data, location):
            try:
                resolve_identifier(identifier, parent, path, vocabulary, uow=uow, session=session)
            except Exception:
                current_app.logger.exception("Error resolving identifier %s at %s", identifier, path)


class FetchIdentifiersComponent(ServiceComponent):
    """Create the vocabulary records missing for a saved record, if CCMM_FETCH_IDENTIFIERS is set."""

    affects = "*"

    def _fetch_identifiers(self, data: dict[str, Any] | None) -> None:
        if current_app.config.get("CCMM_FETCH_IDENTIFIERS") and data:
            resolve_identifiers(data, uow=self.uow)

    def create(self, identity: Any, data: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Fetch the identifiers of a new record or draft."""
        _, _ = identity, kwargs
        self._fetch_identifiers(data)

    def update(self, identity: Any, data: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Fetch the identifiers of an updated record."""
        _, _ = identity, kwargs
        self._fetch_identifiers(data)

    def update_draft(self, identity: Any, data: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Fetch the identifiers of an updated draft."""
        _, _ = identity, kwargs
        self._fetch_identifiers(data)

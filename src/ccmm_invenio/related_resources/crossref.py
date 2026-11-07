# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Crossref work to CCMM record metadata (moved here from oarepo-related-resources' Crossref resolver).

The ``RELATED_RESOURCES_CROSSREF_MAPPER`` of oarepo-related-resources (set to `map_crossref` by
`ccmm_invenio.initial_config`): the Crossref work (the ``message`` of the Crossref REST API response) is
mapped to the metadata of a related resource.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from defusedxml.ElementTree import fromstring
from flask import current_app
from invenio_i18n import lazy_gettext as _
from oarepo_related_resources.resolvers.mapping import ResolverMapping
from oarepo_related_resources.resolvers.utils import handle_errors

from ccmm_invenio.related_resources.utils import build_person_or_org

if TYPE_CHECKING:
    from oarepo_related_resources.resolvers.base import ResolverProblem


class CrossrefMapping(ResolverMapping):
    """Map one Crossref work to CCMM record metadata."""

    provider = "Crossref"

    @override
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        self.resolve_title()
        self.resolve_creators()
        self.resolve_publisher()
        self.resolve_publication_date()
        self.resolve_resource_type()
        self.resolve_description()
        return self.processed_metadata, self.problems

    @handle_errors(alert_user=True)
    def resolve_title(self) -> None:
        """Extract the main title from Crossref metadata."""
        titles = self.metadata.get("title", [])
        if titles:
            self.processed_metadata["title"] = titles[0]

    @handle_errors(alert_user=True)
    def resolve_creators(self) -> None:
        """Extract and map author information from Crossref metadata."""
        creator_list = []
        for crossref_author in self.metadata.get("author", []):
            family = crossref_author.get("family", "")
            given = crossref_author.get("given") or None
            name = f"{family}, {given}" if given else family
            identifiers = None
            orcid = crossref_author.get("ORCID")
            if orcid:
                identifiers = [
                    {
                        "identifier": orcid.removeprefix("https://orcid.org/"),
                        "scheme": "orcid",
                    }
                ]

            creator_list.append(build_person_or_org(name=name, family=family, given=given, identifiers=identifiers))
        if creator_list:
            self.processed_metadata["creators"] = creator_list

    @handle_errors()
    def resolve_publisher(self) -> None:
        """Copy a string publisher from Crossref metadata when present."""
        publisher = self.metadata.get("publisher")
        if isinstance(publisher, str) and publisher:
            self.processed_metadata["publisher"] = publisher

    @handle_errors()
    def resolve_publication_date(self) -> None:
        """Parse and validate publication date parts into an EDTF-compatible string."""
        publication_date_parts = self.metadata.get("published", {}).get("date-parts")
        if not publication_date_parts:
            return
        try:
            parts = publication_date_parts[0]
            if not isinstance(parts, (list, tuple)):
                return
            publication_date = "-".join(f"{x:02d}" for x in parts[:3])
        except Exception as e:  # noqa: BLE001
            self._add_problem(
                _("Invalid publication date-parts format: %s.") % publication_date_parts,
                exc=e,
            )
            return
        self.processed_metadata["publication_date"] = publication_date

    @handle_errors()
    def resolve_resource_type(self) -> None:
        """Set the resource type placeholder for Crossref records."""
        self.processed_metadata["resource_type"] = {"id": current_app.config["RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE"]}

    @handle_errors()
    def resolve_description(self) -> None:
        """Parse and extract plain text abstract from a JATS XML snippet."""
        jats_snippet = self.metadata.get("abstract")
        if not jats_snippet:
            return

        # Crossref often gives fragments, so wrap in a root element
        wrapped = f"<root xmlns:jats='http://www.ncbi.nlm.nih.gov/JATS1'>{jats_snippet}</root>"
        root = fromstring(wrapped)

        parts = []
        for el in root.iter():
            # skip the "Abstract" label/title
            if el.tag.endswith("title"):
                continue
            # capture paragraph text (and any nested text)
            if el.tag.endswith("p"):
                text = "".join(el.itertext()).strip()
                if text:
                    parts.append(text)

        description = "\n\n".join(parts).strip()
        if description:
            self.processed_metadata["description"] = description


def map_crossref(work: dict[str, Any]) -> tuple[dict[str, Any], list[ResolverProblem]]:
    """Map a Crossref work to CCMM record metadata; return ``(metadata, problems)``.

    The ``RELATED_RESOURCES_CROSSREF_MAPPER`` of oarepo-related-resources.
    """
    return CrossrefMapping(work).resolve_metadata()

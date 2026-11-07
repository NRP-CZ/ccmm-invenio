# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Handle landing page to CCMM record metadata (moved here from oarepo-related-resources' Handle resolver).

The ``RELATED_RESOURCES_HANDLE_MAPPER`` of oarepo-related-resources (set to `map_handle` by
`ccmm_invenio.initial_config`): the ``<head>`` of the page a Handle resolves to (an lxml ``HtmlElement``)
is mapped, by its citation / Dublin Core ``<meta>`` tags, to the metadata of a related resource.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Any, override

import dateutil.parser
from flask import current_app
from invenio_i18n import lazy_gettext as _
from oarepo_related_resources.resolvers.utils import (
    build_person_or_org,
    handle_errors,
    resolve_language,
    split_personal_name,
    validate_edtf,
)

from .mapping import ResolverMapping

if TYPE_CHECKING:
    from oarepo_related_resources.resolvers.base import ResolverProblem

MIN_YEAR = 1900


class HandleMapping(ResolverMapping):
    """Map the ``<head>`` of one Handle landing page to CCMM record metadata."""

    provider = "Handle"

    @override
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        self.resolve_title()
        self.resolve_creators()
        self.resolve_publication_date()
        self.resolve_resource_type()
        self.resolve_additional_descriptions()
        return self.processed_metadata, self.problems

    @handle_errors(alert_user=True)
    def resolve_title(self) -> None:
        """Extract the main title from Handle HTML metadata."""
        titles = self.metadata.xpath('//meta[@name="citation_title"]/@content') or self.metadata.xpath(
            '//meta[@name="title"]/@content'
        )
        if titles:
            self.processed_metadata["title"] = titles[0]

    @handle_errors(alert_user=True)
    def resolve_creators(self) -> None:
        """Extract and map creator information from Handle HTML metadata."""
        creators = self.metadata.xpath('//meta[@name="citation_author"]/@content')
        creator_list = []
        for creator in creators:
            # best guess from looking at LINDAT data
            if "," in creator:
                family, given = split_personal_name(creator)
                creator_list.append(build_person_or_org(name=creator, family=family, given=given))
            else:
                creator_list.append(build_person_or_org(name=creator, type_="organizational"))

        if creator_list:
            self.processed_metadata["creators"] = creator_list

    @handle_errors(alert_user=True)
    def resolve_publication_date(self) -> None:
        """Extract and validate the publication date from Handle HTML metadata."""
        dates = (
            self.metadata.xpath('//meta[@name="citation_publication_date"]/@content')
            or self.metadata.xpath('//meta[@name="publication_date"]/@content')
            or self.metadata.xpath('//meta[@name="citation_date"]/@content')
        )
        if not dates:
            return

        parsed = self._parse_loose_date(dates[0])
        if parsed:
            self.processed_metadata["publication_date"] = parsed

    @handle_errors()
    def resolve_resource_type(self) -> None:
        """Set the resource type placeholder for Handle records."""
        # there are dataset related tags, dataset_creator, dataset_license, dataset_keyword ..
        # but they are used also on things that aren't datasets
        self.processed_metadata["resource_type"] = {"id": current_app.config["RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE"]}

    @handle_errors()
    def resolve_additional_descriptions(self) -> None:
        """Extract and map additional descriptions from Handle HTML metadata."""
        descriptions = self.metadata.xpath('//meta[@name="DCTERMS.abstract"]')
        des_list = []
        for d in descriptions:
            description = d.get("content")

            if description:
                description_obj = {}
                d_lang = d.get("xml:lang")
                lang = resolve_language(d_lang)
                if lang:
                    description_obj["lang"] = {"id": lang}
                description_obj["type"] = {"id": "abstract"}
                description_obj["description"] = description
                des_list.append(description_obj)

        if des_list:
            self.processed_metadata["additional_descriptions"] = des_list

    def _parse_loose_date(self, date: str) -> str | None:
        """Parse a free-form date string, falling back to dateutil with a warning."""
        # 0000 is a special case happening a lot in LINDAT data that passes EDTF schema validation
        if re.match(r"^\d{4}$", date) and not (MIN_YEAR < int(date) <= dt.datetime.now(dt.UTC).year):
            self._add_problem(_("Invalid publication date format: %(date)s.", date=date))
            return None
        if validate_edtf(date) is None:
            return date
        try:
            parsed = dateutil.parser.parse(date, fuzzy=True)
        except dateutil.parser.ParserError:
            self._add_problem(_("Invalid publication date format: %(date)s.", date=date))
            return None
        self._add_problem(
            _(
                "Publication date format did not pass validation; format: %(date)s.",
                date=date,
            ),
        )
        return dt.datetime.strftime(parsed, "%Y-%m-%d")


def map_handle(head: Any) -> tuple[dict[str, Any], list[ResolverProblem]]:
    """Map the ``<head>`` of a Handle landing page to CCMM record metadata; return ``(metadata, problems)``.

    The ``RELATED_RESOURCES_HANDLE_MAPPER`` of oarepo-related-resources.
    """
    return HandleMapping(head).resolve_metadata()

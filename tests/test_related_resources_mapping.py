# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Crossref / Handle -> CCMM metadata (moved here from oarepo-related-resources' resolvers)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from lxml import html

from ccmm_invenio.related_resources import handle as handle_module
from ccmm_invenio.related_resources.crossref import CrossrefMapping, map_crossref
from ccmm_invenio.related_resources.handle import HandleMapping, map_handle

# the "message" of https://api.crossref.org/works/doi/10.1575/1912/1099 (shortened)
CROSSREF_WORK = {
    "publisher-location": "Cambridge, MA",
    "publisher": "Massachusetts Institute of Technology and Woods Hole Oceanographic Institution",
    "published-print": {"date-parts": [[1940]]},
    "DOI": "10.1575/1912/1099",
    "type": "monograph",
    "title": [
        "Observations of vertical humidity distribution above the ocean surface and their relation to evaporation"
    ],
    "author": [{"given": "Raymond B.", "family": "Montgomery", "sequence": "first", "affiliation": []}],
    "language": "en",
    "issued": {"date-parts": [[1940]]},
    "URL": "https://doi.org/10.1575/1912/1099",
    "published": {"date-parts": [[1940]]},
}

# the <meta> tags of the landing page of http://hdl.handle.net/11234/1-6144 the mapping reads
HANDLE_HEAD = """
<html><head>
  <meta name="title" content="SiR 2.0">
  <meta name="citation_title" content="SiR 2.0">
  <meta name="citation_author" content="Mírovský, Jiří">
  <meta name="citation_publication_date" content="2026-04-30">
  <meta name="citation_date" content="2026-04-30">
</head></html>
"""


def handle_head(page: str):
    return html.fromstring(page).xpath("/html/head")[0]


def test_map_crossref(app):
    metadata, problems = map_crossref(CROSSREF_WORK)
    assert problems == []
    assert metadata == {
        "creators": [
            {
                "person_or_org": {
                    "family_name": "Montgomery",
                    "given_name": "Raymond B.",
                    "name": "Montgomery, Raymond B.",
                    "type": "personal",
                }
            }
        ],
        "publication_date": "1940",
        "publisher": "Massachusetts Institute of Technology and Woods Hole Oceanographic Institution",
        "resource_type": {"id": "dataset"},
        "title": "Observations of vertical humidity distribution above the ocean surface and their relation to "
        "evaporation",
    }


def test_crossref_author_orcid(app):
    metadata, _ = map_crossref({"author": [{"family": "Novák", "ORCID": "https://orcid.org/0000-0002-1825-0097"}]})
    assert metadata["creators"] == [
        {
            "person_or_org": {
                "family_name": "Novák",
                "identifiers": [{"identifier": "0000-0002-1825-0097", "scheme": "orcid"}],
                "name": "Novák",
                "type": "personal",
            }
        }
    ]


def test_crossref_resolve_description(app):
    mapping = CrossrefMapping(
        {
            "abstract": """
                <jats:title>Abstract</jats:title>
                <jats:p>First paragraph with <jats:bold>bold text</jats:bold>.</jats:p>
                <jats:p>Second paragraph.</jats:p>
            """
        }
    )

    mapping.resolve_description()

    assert mapping.processed_metadata == {"description": "First paragraph with bold text.\n\nSecond paragraph."}


def test_crossref_invalid_date_parts(app):
    metadata, problems = map_crossref({"published": {"date-parts": [["x"]]}})
    assert "publication_date" not in metadata
    assert [str(problem.message) for problem in problems] == ["Invalid publication date-parts format: [['x']]."]
    assert problems[0].resolver == "Crossref"


def test_map_handle(app):
    metadata, problems = map_handle(handle_head(HANDLE_HEAD))
    assert problems == []
    assert metadata == {
        "creators": [
            {
                "person_or_org": {
                    "family_name": "Mírovský",
                    "given_name": "Jiří",
                    "name": "Mírovský, Jiří",
                    "type": "personal",
                }
            }
        ],
        "publication_date": "2026-04-30",
        "resource_type": {"id": "dataset"},
        "title": "SiR 2.0",
    }


def test_handle_organizational_creator(app):
    metadata, _ = map_handle(
        handle_head('<html><head><meta name="citation_author" content="Charles University"></head></html>')
    )
    assert metadata["creators"] == [{"person_or_org": {"name": "Charles University", "type": "organizational"}}]


def test_handle_resolve_additional_descriptions(app, monkeypatch):
    mapping = HandleMapping(
        handle_head(
            """
            <html><head>
              <meta name="DCTERMS.abstract" content="English abstract" xml:lang="en">
              <meta name="DCTERMS.abstract" content="Abstract without language">
            </head></html>
            """
        )
    )
    monkeypatch.setattr(handle_module, "resolve_language", Mock(side_effect=["eng", None]))

    mapping.resolve_additional_descriptions()

    assert mapping.processed_metadata == {
        "additional_descriptions": [
            {
                "lang": {"id": "eng"},
                "type": {"id": "abstract"},
                "description": "English abstract",
            },
            {
                "type": {"id": "abstract"},
                "description": "Abstract without language",
            },
        ]
    }


def test_handle_parse_loose_date(app):
    mapping = HandleMapping(None)

    assert mapping._parse_loose_date("January 2, 2020") == "2020-01-02"
    assert str(mapping.problems[0].message) == (
        "Publication date format did not pass validation; format: January 2, 2020."
    )
    assert mapping.problems[0].resolver == "Handle"


@pytest.mark.parametrize("date", ["not a date", "0000"])
def test_handle_rejects_invalid_date(app, date):
    mapping = HandleMapping(None)

    assert mapping._parse_loose_date(date) is None
    assert str(mapping.problems[0].message) == f"Invalid publication date format: {date}."


@pytest.mark.parametrize(
    ("config_key", "mapper"),
    [
        ("RELATED_RESOURCES_DATACITE_MAPPER", "ccmm_invenio.resources.deserializers.datacite:map_datacite"),
        ("RELATED_RESOURCES_CROSSREF_MAPPER", "ccmm_invenio.related_resources.crossref:map_crossref"),
        ("RELATED_RESOURCES_HANDLE_MAPPER", "ccmm_invenio.related_resources.handle:map_handle"),
    ],
)
def test_related_resources_mappers_are_configured(app, config_key, mapper):
    """ccmm-invenio's initial_config points the related-resources resolvers to its mappings."""
    assert app.config[config_key] == mapper

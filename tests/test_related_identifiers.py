#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

from ccmm_invenio.services.components.related_identifiers import RelatedIdentifiersComponent, related_identifiers

REFERENCED_BY = {"id": "isreferencedby"}
ARTICLE = {"id": "publication-article"}


def test_identifiers_iri_and_resource_url(app):
    assert related_identifiers(
        [
            {
                "title": "An article",
                "relation_type": REFERENCED_BY,
                "resource_type": ARTICLE,
                "identifiers": [{"identifier": "10.1234/abc", "scheme": "doi"}],
                # the same doi as an url - a duplicate
                "iri": "https://doi.org/10.1234/abc",
                "resource_url": "https://journal.org/articles/abc",
            }
        ]
    ) == [
        {"identifier": "10.1234/abc", "scheme": "doi", "relation_type": REFERENCED_BY, "resource_type": ARTICLE},
        {
            "identifier": "https://journal.org/articles/abc",
            "scheme": "url",
            "relation_type": REFERENCED_BY,
            "resource_type": ARTICLE,
        },
    ]


def test_not_related_identifiers(app):
    assert (
        related_identifiers(
            [
                # no relation type - required in RDM
                {"title": "No relation", "iri": "https://example.org/a"},
                # identifiers RDM does not accept: a scheme not allowed for related identifiers
                # (RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES) and an invalid doi
                {
                    "title": "Not accepted",
                    "relation_type": REFERENCED_BY,
                    "identifiers": [
                        {"identifier": "0000-0002-1825-0097", "scheme": "orcid"},
                        {"identifier": "not a doi", "scheme": "doi"},
                    ],
                },
            ]
        )
        == []
    )


def test_resource_type_is_optional(app):
    assert related_identifiers(
        [{"title": "A", "relation_type": REFERENCED_BY, "resource_url": "https://example.org/a"}]
    ) == [{"identifier": "https://example.org/a", "scheme": "url", "relation_type": REFERENCED_BY}]


def test_component_overwrites(app):
    record = {
        "metadata": {
            "related_resources": [{"title": "A", "relation_type": REFERENCED_BY, "iri": "https://example.org/a"}],
            # anything else is overwritten
            "related_identifiers": [{"identifier": "10.1/x", "scheme": "doi", "relation_type": {"id": "cites"}}],
        }
    }
    RelatedIdentifiersComponent(service=None).update_draft(None, data={}, record=record)
    assert record["metadata"]["related_identifiers"] == [
        {"identifier": "https://example.org/a", "scheme": "url", "relation_type": REFERENCED_BY}
    ]

    # no related resources - no related identifiers
    record["metadata"]["related_resources"] = []
    RelatedIdentifiersComponent(service=None).update_draft(None, data={}, record=record)
    assert "related_identifiers" not in record["metadata"]

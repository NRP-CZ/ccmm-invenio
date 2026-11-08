# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Vocabulary records created from the identifiers of a saved record."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from invenio_access.permissions import system_identity
from invenio_records.systemfields.relations import InvalidRelationValue
from invenio_records_resources.proxies import current_service_registry
from oarepo_related_resources import session as session_module

from ccmm_invenio.services.components import fetch_identifiers
from ccmm_invenio.services.components.fetch_identifiers import FetchIdentifiersComponent, resolve_identifiers
from tests.model import ccmm_dataset

ROR = "037n8p820"
ROR_RESPONSE = {
    "id": f"https://ror.org/{ROR}",
    "names": [{"value": "Ministry of Education", "types": ["ror_display"], "lang": "en"}],
    "locations": [{"geonames_details": {"name": "Prague", "country_code": "CZ", "country_name": "Czechia"}}],
    "external_ids": [],
    "types": ["funder"],
    "status": "active",
}


def record_data(funder):
    return {
        "files": {"enabled": False},
        "metadata": {
            "title": "test",
            "publication_date": "2022-01-01",
            "resource_type": {"id": "dataset"},
            "creators": [{"person_or_org": {"type": "personal", "given_name": "John", "family_name": "Doe"}}],
            "related_resources": [
                {
                    "title": "Related",
                    "funding": [{"funder": funder}],
                    "creators": [
                        {
                            "person_or_org": {"type": "personal", "given_name": "Jane", "family_name": "Roe"},
                            "affiliations": [{"id": funder["id"]}],
                        }
                    ],
                }
            ],
        },
    }


@pytest.fixture
def resolved(monkeypatch):
    """Replace the resolvers, return the (value, vocabulary, parent) they were called with."""
    calls = []

    def resolver(value, vocabulary, parent, **_kwargs):
        calls.append((value, vocabulary, parent))
        return {"id": value.removeprefix("https://ror.org/")}

    monkeypatch.setattr(
        fetch_identifiers,
        "IDENTIFIER_RESOLVERS",
        dict.fromkeys(fetch_identifiers.IDENTIFIER_RESOLVERS, resolver),
    )
    return calls


def test_identifiers_are_found_everywhere(app, resolved):
    identifiers = [{"identifier": "0000-1", "scheme": "orcid"}, {"identifier": "x", "scheme": "isni"}]
    person = {"name": "Doe", "identifiers": identifiers}
    data = {
        "metadata": {
            "creators": [{"person_or_org": person, "affiliations": [{"id": "aff"}, {"name": "no id"}]}],
            "contributors": [{"person_or_org": {"identifiers": [{"identifier": "0000-2", "scheme": "orcid"}]}}],
            "funding": [
                {
                    "funder": {"id": "https://ror.org/own", "name": "normalized"},
                    "award": {"identifiers": [{"identifier": "https://example.org", "scheme": "url"}]},
                },
                {"funder": {"name": "no id"}},
            ],
            "metadata_identifications": [
                {
                    "qualified_relations": [
                        {
                            "person_or_org": {"identifiers": [{"identifier": "0000-3", "scheme": "orcid"}]},
                            "affiliations": [{"id": "metadata-record"}],
                        }
                    ]
                }
            ],
            "related_resources": [
                {
                    "funding": [{"funder": {"id": "related"}}],
                    "creators": [
                        {
                            "person_or_org": {"identifiers": [{"identifier": "0000-4", "scheme": "orcid"}]},
                            "affiliations": [{"id": "related-creator"}],
                        }
                    ],
                    "contributors": [{"affiliations": [{"id": "related-contributor"}]}],
                }
            ],
        }
    }

    resolve_identifiers(data)

    assert [(value, vocabulary) for value, vocabulary, _parent in resolved] == [
        ("0000-1", "names"),
        ("aff", "affiliations"),
        ("0000-2", "names"),
        ("https://ror.org/own", "funders"),
        ("0000-3", "names"),
        ("metadata-record", "affiliations"),
        ("related", "funders"),
        ("related-creator", "affiliations"),
        ("related-contributor", "affiliations"),
    ]
    # the person is the fallback of the names ORCID does not make public
    assert resolved[0][2] is person
    assert data["metadata"]["funding"][0]["funder"]["id"] == "own"


def test_all_relations_to_affiliations_and_funders_are_covered(app):
    relations = {name for name in ccmm_dataset.Draft.relations._fields if name.endswith((".affiliations", ".funder"))}

    assert relations
    assert relations <= fetch_identifiers.IDENTIFIER_LOCATIONS.keys()


def test_a_failing_identifier_does_not_stop_the_others(app, monkeypatch):
    resolver = Mock(side_effect=[ValueError("ror.org is down"), {"id": "good"}])
    monkeypatch.setitem(fetch_identifiers.IDENTIFIER_RESOLVERS, ("funders", None), resolver)
    data = {"metadata": {"funding": [{"funder": {"id": "bad"}}, {"funder": {"id": "good"}}]}}

    resolve_identifiers(data)

    assert resolver.call_count == 2
    assert data["metadata"]["funding"][0]["funder"]["id"] == "bad"


@pytest.mark.parametrize("method", ["create", "update", "update_draft"])
@pytest.mark.parametrize(("enabled", "expected"), [(False, []), (True, ["own"])])
def test_component_is_switched_by_the_config(app, resolved, monkeypatch, method, enabled, expected):
    monkeypatch.setitem(app.config, "CCMM_FETCH_IDENTIFIERS", enabled)
    component = FetchIdentifiersComponent(service=None)
    component.uow = Mock()

    getattr(component, method)(None, data={"metadata": {"funding": [{"funder": {"id": "own"}}]}}, record={})

    assert [value for value, _vocabulary, _parent in resolved] == expected


def test_unknown_funder_and_affiliation_of_a_related_resource_are_created(
    app, db, identity_simple, search, location, vocab_fixtures, monkeypatch
):
    monkeypatch.setitem(app.config, "CCMM_FETCH_IDENTIFIERS", True)  # noqa
    monkeypatch.setitem(app.config, "ROR_CLIENT_ID", "test")
    session = SimpleNamespace(get=Mock(return_value=SimpleNamespace(status_code=200, json=lambda: ROR_RESPONSE)))
    monkeypatch.setattr(session_module, "create_session_with_retries", lambda: session)

    rec = ccmm_dataset.proxies.current_service.create(identity_simple, data=record_data({"id": ROR, "name": "x"}))

    assert rec.to_dict()["metadata"]["related_resources"][0]["funding"][0]["funder"]["id"] == ROR
    funder = current_service_registry.get("funders").read(system_identity, ROR).to_dict()
    assert funder["name"] == "Ministry of Education"
    affiliation = current_service_registry.get("affiliations").read(system_identity, ROR).to_dict()
    assert affiliation["name"] == "Ministry of Education"


def test_nothing_is_downloaded_when_not_configured(
    app, db, identity_simple, search, location, vocab_fixtures, monkeypatch
):
    monkeypatch.setitem(app.config, "CCMM_FETCH_IDENTIFIERS", False)  # noqa
    create_session = Mock()
    monkeypatch.setattr(session_module, "create_session_with_retries", create_session)

    with pytest.raises(InvalidRelationValue):
        ccmm_dataset.proxies.current_service.create(identity_simple, data=record_data({"id": "01pv73b02", "name": "x"}))

    create_session.assert_not_called()

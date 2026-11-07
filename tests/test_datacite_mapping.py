# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""DataCite JSON -> CCMM metadata (moved here from oarepo-related-resources' DataCite resolver)."""

from __future__ import annotations

import json
from unittest.mock import Mock

import oarepo_related_resources.services as services
import pytest
from marshmallow import ValidationError
from oarepo_related_resources.resolvers.base import ResolverProblem, ResolverProblemLevel

from ccmm_invenio.resources.deserializers import datacite as datacite_module
from ccmm_invenio.resources.deserializers.datacite import DataCiteJSONDeserializer, DataCiteMapping, map_datacite


def test_datacite_descriptions_and_subjects(app, monkeypatch):
    mapping = DataCiteMapping({})
    mapping.metadata = {
        "descriptions": [
            {"descriptionType": "Abstract", "description": "Main abstract"},
            {"descriptionType": "Methods", "description": "Used methods", "lang": "en"},
            {"descriptionType": "Other", "description": "Missing language"},
        ],
        "subjects": [
            {"subject": "biology"},
            {"subject": "biology"},
            {"subject": "chemistry"},
            "invalid",
        ],
    }
    monkeypatch.setattr(datacite_module, "vocabulary_entry_exists", Mock(return_value=True))
    monkeypatch.setattr(datacite_module, "resolve_language", Mock(return_value="eng"))

    mapping.resolve_description()
    mapping.resolve_additional_descriptions()
    mapping.resolve_subjects()

    assert mapping.processed_metadata == {
        "description": "Main abstract",
        "additional_descriptions": [
            {
                "type": {"id": "methods"},
                "description": "Used methods",
                "lang": {"id": "eng"},
            }
        ],
        "subjects": [{"subject": "biology"}, {"subject": "chemistry"}],
    }


def test_datacite_related_titles_and_contributors(app, monkeypatch):
    mapping = DataCiteMapping({})
    mapping.metadata = {
        "titles": [
            {"title": "Main title"},
            {"title": "Translated title", "titleType": "TranslatedTitle", "lang": "cs"},
        ],
        "relatedIdentifiers": [
            {
                "relatedIdentifier": "10.1234/related",
                "relatedIdentifierType": "DOI",
                "relationType": "References",
                "resourceTypeGeneral": "Dataset",
            }
        ],
        "contributors": [{"name": "Lovelace, Ada", "contributorType": "Editor"}],
    }
    monkeypatch.setattr(
        datacite_module,
        "lookup_vocabulary_by_prop",
        Mock(side_effect=["translated-title", "references", "editor"]),
    )
    monkeypatch.setattr(
        datacite_module,
        "lookup_vocabulary_by_prop_handle_multiple",
        Mock(return_value="dataset"),
    )
    monkeypatch.setattr(datacite_module, "resolve_language", Mock(return_value="ces"))

    mapping.resolve_additional_titles()
    mapping.resolve_related_identifiers()
    mapping.resolve_contributors()

    assert mapping.processed_metadata == {
        "additional_titles": [
            {
                "title": "Translated title",
                "type": {"id": "translated-title"},
                "lang": {"id": "ces"},
            }
        ],
        "related_identifiers": [
            {
                "identifier": "10.1234/related",
                "scheme": "doi",
                "relation_type": {"id": "references"},
                "resource_type": {"id": "dataset"},
            }
        ],
        "contributors": [
            {
                "person_or_org": {
                    "name": "Lovelace, Ada",
                    "type": "personal",
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                },
                "role": {"id": "editor"},
            }
        ],
    }


def test_datacite_affiliations_and_name_identifiers(app, monkeypatch):
    mapping = DataCiteMapping({})
    monkeypatch.setattr(services, "resolve_orcid", Mock(return_value={"id": "0000-0001"}))

    assert (
        mapping._resolve_datacite_affiliations(
            [
                "Institute",
                "Institute",
                {"affiliationIdentifierScheme": "ROR", "affiliationIdentifier": "01abc"},
                {"name": "Named institute"},
            ]
        ),
        mapping._resolve_datacite_name_identifiers(
            name_identifiers=[
                {"nameIdentifier": "https://orcid.org/0000-0001", "nameIdentifierScheme": "ORCID"},
                {"nameIdentifier": "https://orcid.org/0000-0001", "nameIdentifierScheme": "ORCID"},
                {"nameIdentifier": "ignored", "nameIdentifierScheme": "unknown"},
            ]
        ),
    ) == (
        [{"name": "Institute"}, {"name": "01abc"}, {"name": "Named institute"}],
        [{"identifier": "0000-0001", "scheme": "orcid"}],
    )


@pytest.mark.parametrize(
    ("titles", "title"),
    [
        # DataCite REST API sends the titleType of the main title as null
        ([{"title": "Main", "titleType": None}, {"title": "Alt", "titleType": "AlternativeTitle"}], "Main"),
        # no main title - the first title is used
        ([{"title": None}, {"title": "Alt", "titleType": "AlternativeTitle"}], "Alt"),
    ],
)
def test_datacite_title(app, monkeypatch, titles, title):
    mapping = DataCiteMapping({})
    mapping.metadata = {"titles": titles}
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop", Mock(return_value="alternative-title"))

    mapping.resolve_title()
    mapping.resolve_additional_titles()

    assert mapping.processed_metadata["title"] == title
    # a title is never repeated in the additional titles
    assert title not in [t["title"] for t in mapping.processed_metadata.get("additional_titles", [])]


def test_datacite_additional_title_without_value_is_omitted(app, monkeypatch):
    mapping = DataCiteMapping({})
    mapping.metadata = {"titles": [{"title": "Main"}, {"title": None, "titleType": "AlternativeTitle"}]}
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop", Mock(return_value="alternative-title"))

    mapping.resolve_title()
    mapping.resolve_additional_titles()

    assert "additional_titles" not in mapping.processed_metadata


def test_datacite_invalid_values_are_omitted(app, monkeypatch):
    """Values the record schema would reject are dropped, the rest of the record is kept."""
    mapping = DataCiteMapping({})
    mapping.metadata = {
        "relatedIdentifiers": [
            {"relationType": "IsCitedBy", "relatedIdentifierType": "DOI"},
            {"relationType": "References", "relatedIdentifier": ["10.1234/a"], "relatedIdentifierType": "DOI"},
            {"relationType": "References", "relatedIdentifier": "10.1234/valid", "relatedIdentifierType": "DOI"},
        ],
        "dates": [{"date": "", "dateType": "Issued"}, {"date": "2020-01-31", "dateType": "Issued"}],
        "identifiers": [
            {"identifier": "CEH:EIDC:#1406898956642", "identifierType": "URN"},
            {"identifier": "urn:nbn:cz:123", "identifierType": "URN"},
        ],
    }
    monkeypatch.setattr(
        datacite_module, "lookup_vocabulary_by_prop", Mock(side_effect=lambda _vocab, value: value.lower())
    )
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop_handle_multiple", Mock(return_value=None))

    mapping.resolve_related_identifiers()
    mapping.resolve_dates()
    mapping.resolve_identifiers()

    assert mapping.processed_metadata == {
        "related_identifiers": [
            {"identifier": "10.1234/valid", "scheme": "doi", "relation_type": {"id": "references"}},
        ],
        "dates": [{"date": "2020-01-31", "type": {"id": "issued"}}],
        "identifiers": [{"identifier": "urn:nbn:cz:123", "scheme": "urn"}],
    }
    # dropped values are reported, but not as errors
    assert len(mapping.problems) == 4
    assert {p.level for p in mapping.problems} == {datacite_module.ResolverProblemLevel.INFO}


def test_map_datacite_returns_metadata_and_problems(app, monkeypatch):
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop_handle_multiple", Mock(return_value=None))
    metadata, problems = map_datacite({"titles": [{"title": "Main"}], "publisher": {"name": "Pub"}})

    assert metadata["title"] == "Main"
    assert metadata["publisher"] == "Pub"
    # the unmapped resource type falls back to the default and is reported
    assert metadata["resource_type"] == {"id": app.config["RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE"]}
    assert [p.level for p in problems] == [ResolverProblemLevel.WARNING]


def test_related_resources_ui_schema_is_configured(app):
    """ccmm-invenio's initial_config wins over the RDM default of oarepo-related-resources (setdefault)."""
    assert app.config["RELATED_RESOURCES_RECORD_UI_SCHEMA"] == (
        "ccmm_invenio.resources.serializers.ui.related_resources.CCMMRelatedResourceUISchema"
    )


@pytest.mark.parametrize(
    "document",
    [
        {"titles": [{"title": "Main"}]},
        # the DataCite REST API response is accepted as well
        {"data": {"attributes": {"titles": [{"title": "Main"}]}}},
    ],
)
def test_deserializer_maps_attributes(app, monkeypatch, document):
    mapper = Mock(return_value=({"title": "Main"}, []))
    monkeypatch.setattr(datacite_module, "map_datacite", mapper)

    assert DataCiteJSONDeserializer().deserialize(json.dumps(document).encode()) == {"metadata": {"title": "Main"}}
    mapper.assert_called_once_with({"titles": [{"title": "Main"}]})


def test_deserializer_fails_on_mapping_errors(app, monkeypatch):
    problems = [
        ResolverProblem(resolver="Datacite", message="dropped", level=ResolverProblemLevel.INFO),
        ResolverProblem(resolver="Datacite", message="broken creators", level=ResolverProblemLevel.ERROR),
    ]
    monkeypatch.setattr(datacite_module, "map_datacite", Mock(return_value=({}, problems)))

    with pytest.raises(ValidationError) as exc:
        DataCiteJSONDeserializer().deserialize(b"{}")
    assert exc.value.messages == ["broken creators"]


def test_deserializer_rejects_non_object(app):
    with pytest.raises(ValidationError):
        DataCiteJSONDeserializer().deserialize(b"[]")

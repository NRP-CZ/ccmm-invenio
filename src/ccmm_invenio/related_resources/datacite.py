# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""DataCite attributes to CCMM record metadata.

The DataCite attributes object (``titles``, ``creators``, ``publicationYear``, ... - the ``data.attributes``
of the DataCite REST API, without the wrapper) is mapped to the ``metadata`` of a CCMM record. Values that
can not be mapped are left out and reported as problems, the rest of the record is kept.

Two callers use the mapping:

* the DataCite resolver of oarepo-related-resources, through the ``RELATED_RESOURCES_DATACITE_MAPPER``
  config (set to `map_datacite` by `ccmm_invenio.initial_config`), to prefill a related resource,
* `ccmm_invenio.resources.deserializers.datacite.DataCiteJSONDeserializer`, the model's ``datacite-json``
  import (used e.g. by the RO-Crate import).
"""

from __future__ import annotations

import re
from typing import Any, override

from flask import current_app
from invenio_access.permissions import system_identity
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.schemas.metadata import (
    record_identifiers_schemes,
    record_personorg_schemes,
    record_related_identifiers_schemes,
)
from invenio_records_resources.proxies import current_service_registry
from marshmallow import ValidationError
from marshmallow_utils.fields import EDTFDateTimeString
from marshmallow_utils.schemas import IdentifierSchema
from oarepo_related_resources.resolvers.base import ResolverProblem, ResolverProblemLevel
from oarepo_related_resources.resolvers.mapping import ResolverMapping
from oarepo_related_resources.resolvers.utils import (
    escape_lucene,
    handle_errors,
    lookup_vocabulary_by_prop,
    lookup_vocabulary_by_prop_handle_multiple,
    normalize_date,
    resolve_language,
    split_personal_name,
    vocabulary_entry_exists,
)

from ccmm_invenio.related_resources.utils import build_person_or_org


def _is_valid_identifier(identifier: Any, scheme: str, schemes: Any) -> bool:
    """Check the identifier the same way as the record schema does."""
    try:
        IdentifierSchema(allowed_schemes=schemes).load({"identifier": identifier, "scheme": scheme})
    except ValidationError:
        return False
    return True


def _is_valid_date(date: str | None) -> bool:
    """Check the date the same way as the record schema does."""
    try:
        EDTFDateTimeString().deserialize(date)
    except ValidationError:
        return False
    return True


def _non_empty_str(value: Any) -> str | None:
    """Return the value if it is a non-empty string - source records may contain nulls or other types."""
    return value if isinstance(value, str) and value.strip() else None


class DataCiteMapping(ResolverMapping):
    """Map one DataCite attributes object to CCMM record metadata."""

    provider = "Datacite"

    @override
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Map the whole attributes object, return the metadata and the problems."""
        self.resolve_title()
        self.resolve_creators()
        self.resolve_additional_titles()
        self.resolve_publication_date()
        self.resolve_resource_type()
        self.resolve_publisher()
        self.resolve_contributors()
        self.resolve_description()
        self.resolve_dates()
        self.resolve_subjects()
        self.resolve_language()
        self.resolve_related_identifiers()
        self.resolve_additional_descriptions()
        self.resolve_sizes()
        self.resolve_formats()
        self.resolve_version()
        self.resolve_rights()
        self.resolve_identifiers()
        return self.processed_metadata, self.problems

    @handle_errors()
    def resolve_additional_descriptions(self) -> None:
        """Extract and map non-abstract descriptions from DataCite metadata."""
        des_list = []
        for d in self.metadata.get("descriptions", []):
            _type = d.get("descriptionType")
            description = d.get("description")

            if description and isinstance(_type, str) and _type != "Abstract" and isinstance(description, str):
                d_type = re.sub(r"(?<!^)([A-Z])", r"-\1", _type).lower()
                if not vocabulary_entry_exists("descriptiontypes", d_type):
                    self._add_problem(
                        _("The description type '%(type)s' could not be mapped, so the description was omitted.")
                        % {"type": d_type},
                        level=ResolverProblemLevel.INFO,
                    )
                    continue
                description_obj: dict[str, Any] = {}
                description_obj["type"] = {"id": d_type}
                description_obj["description"] = description
                d_lang = d.get("lang")
                if not isinstance(d_lang, str):
                    self._add_problem(
                        _("The language '%(type)s' could not be mapped, so the description was omitted.")
                        % {"type": d_lang},
                        level=ResolverProblemLevel.INFO,
                    )
                    continue
                lang = resolve_language(d_lang)
                if lang:
                    description_obj["lang"] = {"id": lang}
                des_list.append(description_obj)
        if des_list:
            self.processed_metadata["additional_descriptions"] = des_list

    @handle_errors()
    def resolve_description(self) -> None:
        """Extract the abstract description from DataCite metadata."""
        for d in self.metadata.get("descriptions", []):
            _type = d.get("descriptionType")
            description = d.get("description")
            if _type == "Abstract":
                self.processed_metadata["description"] = description
                break

    @handle_errors()
    def resolve_language(self) -> None:
        """Resolve and validate the language of the record."""
        datacite_language = self.metadata.get("language")
        language = resolve_language(datacite_language)
        if language:
            self.processed_metadata["languages"] = [{"id": language}]

    @handle_errors()
    def resolve_related_identifiers(self) -> None:
        """Resolve and validate related identifiers and their relation types."""
        result = []
        for rel in self.metadata.get("relatedIdentifiers", []):
            identifier = _non_empty_str(rel.get("relatedIdentifier"))
            scheme = (_non_empty_str(rel.get("relatedIdentifierType")) or "").lower()
            rel_type = rel.get("relationType")
            if not identifier or not _is_valid_identifier(identifier, scheme, record_related_identifiers_schemes):
                self._add_problem(
                    _("The related identifier '%(identifier)s' is not valid, so it was omitted.")
                    % {"identifier": identifier},
                    level=ResolverProblemLevel.INFO,
                )
                continue
            obj: dict[str, Any] = {"identifier": identifier, "scheme": scheme}
            resolved_rel_type = lookup_vocabulary_by_prop("relationtypes", rel_type)
            if resolved_rel_type is None:  # no duplicate values found in rdm fixtures
                self._add_problem(
                    _("The relation type '%(type)s' could not be mapped, so the related identifier was omitted.")
                    % {"type": rel_type},
                    level=ResolverProblemLevel.INFO,
                )
                continue
            obj["relation_type"] = {"id": resolved_rel_type}

            res_type = rel.get("resourceTypeGeneral")
            if res_type:
                # duplicate values possible here
                resolved_type = lookup_vocabulary_by_prop_handle_multiple(
                    "resourcetypes", res_type, prop="datacite_general"
                )
                if resolved_type is not None:
                    obj["resource_type"] = {"id": resolved_type}

            result.append(obj)

        if result:
            self.processed_metadata["related_identifiers"] = result

    @handle_errors()
    def resolve_publication_date(self) -> None:
        """Copy ``publicationYear`` from DataCite metadata into ``publication_date``."""
        publication_date = self.metadata.get("publicationYear")
        if publication_date:
            self.processed_metadata["publication_date"] = str(publication_date)

    @handle_errors()
    def resolve_dates(self) -> None:
        """Validate and map DataCite date entries to the target format."""
        dates_list = []
        for d in self.metadata.get("dates", []):
            date_object: dict[str, Any] = {}
            date = normalize_date(d.get("date"))
            if not _is_valid_date(date):
                self._add_problem(
                    _("The date '%(date)s' is not valid, so it was omitted.") % {"date": d.get("date")},
                    level=ResolverProblemLevel.INFO,
                )
                continue
            _type = d.get("dateType")
            resolved_datatype = lookup_vocabulary_by_prop("datetypes", _type)
            if resolved_datatype is None:
                self._add_problem(
                    _("The date type '%(type)s' could not be mapped, so the date was omitted.") % {"type": _type},
                    level=ResolverProblemLevel.INFO,
                )
                continue
            date_object["date"] = str(date)
            date_object["type"] = {"id": resolved_datatype}
            dates_list.append(date_object)
        if dates_list:
            self.processed_metadata["dates"] = dates_list

    @handle_errors()
    def resolve_rights(self) -> None:
        """Resolve and validate rights identifiers against the licenses vocabulary."""
        rights_list = []
        for r in self.metadata.get("rightsList", []):
            code = r.get("rightsIdentifier")
            if not code:
                continue
            if not vocabulary_entry_exists("licenses", code):
                # SPDX ids are lowercase in the vocabulary, while DataCite
                # commonly emits mixed/upper case (e.g. "CC-BY-4.0")
                lowered = code.lower()
                if lowered != code and vocabulary_entry_exists("licenses", lowered):
                    code = lowered
                else:
                    continue
            rights_list.append({"id": code})
        if rights_list:
            self.processed_metadata["rights"] = rights_list

    @handle_errors()
    def resolve_publisher(self) -> None:
        """Copy the ``publisher`` field from DataCite metadata when present.

        DataCite responses may contain the publisher either as a plain string or
        as an object with a ``name`` property. Different repository instances
        currently return different variants.
        """
        publisher = self.metadata.get("publisher")
        if isinstance(publisher, dict):
            publisher = publisher.get("name")

        if isinstance(publisher, str) and publisher:
            self.processed_metadata["publisher"] = publisher

    @handle_errors()
    def resolve_subjects(self) -> None:
        """Extract unique subject values from DataCite metadata."""
        subjects_list = []
        seen = set()
        for s in self.metadata.get("subjects", []):
            if not isinstance(s, dict):
                continue

            value = s.get("subject")
            if not value or not isinstance(value, str):
                continue
            if value in seen:
                continue
            seen.add(value)
            subjects_list.append({"subject": value})
        if subjects_list:
            self.processed_metadata["subjects"] = subjects_list

    @handle_errors(alert_user=True)
    def resolve_title(self) -> None:
        """Extract the main title from DataCite metadata and validate its length."""
        titles = [t for t in self.metadata.get("titles", []) if _non_empty_str(t.get("title"))]
        # the main title has no titleType - the key is missing or null;
        # without one, take the first title of any type so that the record has a title
        main = next((t for t in titles if not t.get("titleType")), titles[0] if titles else None)
        if main:
            self.processed_metadata["title"] = main["title"]

    @handle_errors()
    def resolve_additional_titles(self) -> None:
        """Extract and map additional titles from DataCite metadata."""
        additional_titles = []
        for title in self.metadata.get("titles", []):
            title_obj = {}
            t_type = title.get("titleType")
            if not t_type or title.get("title") == self.processed_metadata.get("title"):
                # the main title (or another title taken as the main one)
                continue
            if not _non_empty_str(title.get("title")):
                continue
            resolved_type = lookup_vocabulary_by_prop("titletypes", t_type)  # no duplicate values found in rdm fixtures
            if resolved_type is None:
                self._add_problem(
                    _("The title '%(type)s' could not be mapped, so the additional title was omitted.")
                    % {"type": t_type},
                    level=ResolverProblemLevel.INFO,
                )
                continue
            t_lang = None
            title_obj["title"] = title.get("title")
            title_obj["type"] = {"id": resolved_type}

            if "lang" in title:
                t_lang = resolve_language(title["lang"])
            if t_lang:
                title_obj["lang"] = {"id": t_lang}
            additional_titles.append(title_obj)

        if additional_titles:
            self.processed_metadata["additional_titles"] = additional_titles

    @handle_errors(alert_user=True)
    def resolve_creators(self) -> None:
        """Extract and map creator information from DataCite metadata."""
        creators = [self._resolve_datacite_author(creator, "creator") for creator in self.metadata.get("creators", [])]
        creators = [c for c in creators if c is not None]
        if creators:
            self.processed_metadata["creators"] = creators

    @handle_errors()
    def resolve_contributors(self) -> None:
        """Extract and map contributor information including roles and affiliations."""
        contributor_list = []
        for contributor in self.metadata.get("contributors", []):
            entry = self._resolve_datacite_author(contributor, "contributor")
            if not entry:
                continue
            # Resolve contributor role
            role = contributor.get("contributorType")
            resolved_role = lookup_vocabulary_by_prop(
                "contributorsroles", role
            )  # no contributorroles vocabulary in rdm fixtures
            if resolved_role:
                entry["role"] = {"id": resolved_role}
            contributor_list.append(entry)

        if contributor_list:
            self.processed_metadata["contributors"] = contributor_list

    @handle_errors()
    def resolve_resource_type(self) -> None:
        """Resolve and map the DataCite resource type to a vocabulary identifier."""
        resource_type = self.metadata.get("types", {})
        vocabulary_id = "resourcetypes"
        _type = resource_type.get("resourceTypeGeneral") or "Other"

        escaped = escape_lucene(_type)
        if escaped == "Image":
            self.processed_metadata["resource_type"] = {"id": "image"}
            return
        resolved_type = lookup_vocabulary_by_prop_handle_multiple(vocabulary_id, escaped, prop="datacite_general")
        if not resolved_type:
            self._add_problem(
                _("The provided resource type %s could not be parsed. The default value %s has been applied.")
                % (_type, current_app.config["RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE"]),
            )
            self.processed_metadata["resource_type"] = {
                "id": current_app.config["RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE"]
            }
            return
        self.processed_metadata["resource_type"] = {"id": resolved_type}

    @handle_errors()
    def resolve_identifiers(self) -> None:
        """Resolve and map identifiers from DataCite metadata."""
        identifiers = []
        for id_with_scheme in self.metadata.get("identifiers", []):
            identifier = _non_empty_str(id_with_scheme.get("identifier"))
            scheme = (_non_empty_str(id_with_scheme.get("identifierType")) or "").lower()
            if scheme not in record_identifiers_schemes:
                continue
            if not identifier or not _is_valid_identifier(identifier, scheme, record_identifiers_schemes):
                self._add_problem(
                    _("The identifier '%(identifier)s' is not a valid %(scheme)s, so it was omitted.")
                    % {"identifier": identifier, "scheme": scheme},
                    level=ResolverProblemLevel.INFO,
                )
                continue
            identifiers.append({"identifier": identifier, "scheme": scheme})
        if identifiers:
            self.processed_metadata["identifiers"] = identifiers

    @handle_errors()
    def resolve_sizes(self) -> None:
        """Copy the ``sizes`` field from the DataCite metadata when present."""
        val = self.metadata.get("sizes", None)
        if val:
            self.processed_metadata["sizes"] = val

    @handle_errors()
    def resolve_formats(self) -> None:
        """Copy the ``formats`` field from the DataCite metadata when present."""
        val = self.metadata.get("formats", None)
        if val:
            self.processed_metadata["formats"] = val

    @handle_errors()
    def resolve_version(self) -> None:
        """Copy the ``version`` field from the DataCite metadata when present."""
        val = self.metadata.get("version", None)
        if val:
            self.processed_metadata["version"] = val

    @handle_errors()
    def _resolve_datacite_affiliations(self, affiliations: list | None) -> list:  # noqa: C901
        """Extract and normalize affiliation entries while removing duplicates."""
        affiliations_list = []
        seen = set()

        for a in affiliations or []:
            if isinstance(a, str):
                if a in seen:
                    continue
                seen.add(a)
                affiliations_list.append({"name": a})
            elif isinstance(a, dict):
                a_scheme = a.get("affiliationIdentifierScheme")
                name = a.get("name")
                if a_scheme == "ROR":
                    a_identifier = a.get("affiliationIdentifier")
                    if isinstance(a_identifier, str):
                        ror_id = a_identifier.rstrip("/").rsplit("/", 1)[-1]
                        if ror_id in seen:
                            continue
                        try:
                            affiliations_service = current_service_registry.get("affiliations")
                            affiliations_service.read(system_identity, ror_id)  # ty: ignore[unresolved-attribute]
                        except Exception:  # noqa: BLE001
                            name = a.get("name") or a_identifier
                        else:
                            affiliations_list.append({"id": ror_id})
                            seen.add(ror_id)
                            continue
                if not name or not isinstance(name, str):
                    continue
                if name in seen:
                    continue
                seen.add(name)

                affiliations_list.append({"name": name})

        return affiliations_list

    def _resolve_datacite_author(self, author: dict[str, Any], type_: str) -> dict[str, Any] | None:
        author_type = (author.get("nameType") or "personal").lower()
        given = author.get("givenName")
        family = author.get("familyName")
        name = author.get("name")

        if name is None:  # should never happen
            self._add_problem(_("Missing %ss name: %s.") % (type_, author))
            return None

        if author_type == "personal":
            parsed_family, parsed_given = split_personal_name(name)
            family = family or parsed_family
            given = given or (parsed_given or None)

        identifiers = self._resolve_datacite_name_identifiers(name_identifiers=author.get("nameIdentifiers", []))
        affiliations = self._resolve_datacite_affiliations(author.get("affiliation", []))
        return build_person_or_org(
            name=name,
            type_=author_type,
            given=given,
            family=family,
            identifiers=identifiers if isinstance(identifiers, list) else None,
            affiliations=affiliations,
        )

    @handle_errors()
    def _resolve_datacite_name_identifiers(self, *, name_identifiers: list | None) -> list:
        """Resolve and normalize name identifiers including ORCID handling."""
        from oarepo_related_resources.services import resolve_orcid

        identifiers = []
        seen = []
        for ni in name_identifiers or []:
            identifier = ni.get("nameIdentifier")
            scheme = ni.get("nameIdentifierScheme")
            if scheme:
                scheme = scheme.lower()
            if not identifier or not scheme:
                continue
            if scheme not in record_personorg_schemes:
                continue
            if identifier in seen:  # needs to be unique
                continue
            seen.append(identifier)
            if scheme == "orcid":
                try:
                    identifier_dict = resolve_orcid(
                        orcid=identifier,
                        vocabulary="names",
                        parent=ni,
                        create_vocabulary_record=True,
                        check_existing=True,
                    )
                    identifier = identifier_dict["id"]
                except Exception:
                    current_app.logger.exception(
                        "Error resolving ORCID identifier '%s'.",
                        identifier,
                    )
                    continue
            obj = {"identifier": identifier}

            obj["scheme"] = scheme
            identifiers.append(obj)
        return identifiers


def map_datacite(attributes: dict[str, Any]) -> tuple[dict[str, Any], list[ResolverProblem]]:
    """Map DataCite attributes to CCMM record metadata; return ``(metadata, problems)``.

    The ``RELATED_RESOURCES_DATACITE_MAPPER`` of oarepo-related-resources.
    """
    return DataCiteMapping(attributes).resolve_metadata()

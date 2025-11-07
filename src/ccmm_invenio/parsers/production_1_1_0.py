#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Parser for CCMM xml inside deposition repositories.

The metadata model for this repository is called CCMMProductionDataset
and is defined inside the ccmm-invenio.yaml file.

The parser is a top-down recursive descent parser that maps XML elements
to the corresponding fields in the CCMMProductionDataset model. It contains
a sequence of parse_* methods, each responsible for parsing a specific
element from the XML input.

Notes:
1. in xml input, arrays are represented by repeated elements with a singular name.
   In the CCMM model, arrays are represented by json arrays with plural names.
   Create a parse_*_array method that creates the array, calls the parse_* method
   for each element and returns the array.
2. Vocabulary fields (their definition inside the ccmm-vocabularies.yaml file)
   are mapped with calling a special method
   parse_vocabulary_field(vocabularytype, iri from the xml). The fields inside the
   xml schema look like (iri, labels).
3. When element is processed, it should be removed from the etree.
4. After parsing of a record part is finished, the etree is checked to be empty - if not,
   an exception should be raised.
5. do not leave null values in dictionaries or lists - remove them using
    remove_empty_from_dict and remove_empty_from_list methods.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .nma_1_1_0 import CCMMXMLNMAParser

if TYPE_CHECKING:
    from collections.abc import Callable

    from lxml.etree import _Element as Element


log = logging.getLogger(__name__)


class CCMMXMLProductionParserBase:
    """Parser for CCMM XML version 1.1.0 for production repository."""

    def parse(self, xml_root: Element) -> dict[str, Any]:
        """Parse the root element of the CCMM XML record.

        The convert methods used below transform the metadata dictionary in-place.
        """
        # at first, use the NMA parser to convert xml to json
        record: dict[str, Any] = super().parse(xml_root)  # type: ignore[misc]
        metadata = record["metadata"]
        # now, convert the RDM parts
        self.convert_publication_date(metadata)
        self.convert_additional_titles(metadata)
        self.convert_additional_descriptions(metadata)

        self.convert_metadata_identifiers(metadata)

        qualified_relations = metadata.pop("qualified_relations", [])
        qualified_relations = self.convert_publisher(metadata, qualified_relations)
        qualified_relations = self.convert_creators(metadata, qualified_relations)
        qualified_relations = self.convert_contributors(metadata, qualified_relations)
        if qualified_relations != []:
            log.warning(
                "Some qualified relations could not be mapped to creators or contributors and are stripped out: %s",
                qualified_relations,
            )

        self.convert_subjects(metadata)

        self.convert_funding(metadata)

        self.convert_related_resources(metadata)
        self.convert_resource_type(metadata)
        self.convert_languages(metadata)

        # Parts that are unchanged from NMA
        #
        # version is already parsed in NMA in the same format
        # title is already parsed in NMA in the same format
        # locations are already parsed in NMA, we use them as they are
        # provenances are already parsed in NMA, we use them as they are
        # time references are already parsed in NMA, we use them as they are
        # validation_results are already parsed in NMA, we use them as they are
        # terms of use are already parsed in NMA, we use them as they are

        # Ignored parts
        #
        # metadata_identifications:
        # not present in production repository as it is constructed from the technical
        # invenio metadata
        metadata_identifications = metadata.pop("metadata_identifications", None)
        if metadata_identifications is not None:
            log.warning(
                "metadata_identification section is not present in production repository record, stripping out %s",
                metadata_identifications,
            )
        #
        # distributions can not be uploaded this way, so we ignore them
        #
        distributions = metadata.pop("distributions", None)
        if distributions is not None:
            log.warning(
                "distributions section is not present in production repository record, stripping out %s",
                distributions,
            )

        return record

    def convert_additional_titles(self, metadata: dict[str, Any]) -> None:
        """Convert additional titles from NMA format to production format."""
        # RDM's additional_titles are called alternate_titles in NMA
        alternate_titles = metadata.pop("alternate_titles", [])
        if not alternate_titles:
            return

        # in NMA, it is a list of alternate_title_type and title which has lang and value
        # in RDM, it is a list of title, type and lang

        converted_additional_titles = []
        for title in alternate_titles:
            for title_with_lang in title.get("title", []):
                converted_title = {
                    "title": title_with_lang.get("value"),
                    "type": title.get("alternate_title_type"),
                    "lang": title_with_lang.get("lang"),
                }
                converted_additional_titles.append(converted_title)

        metadata["additional_titles"] = converted_additional_titles

    def convert_additional_descriptions(self, metadata: dict[str, Any]) -> None:
        """Convert additional descriptions from NMA format to RDM format."""
        # RDM's additional_descriptions are called descriptions in NMA
        descriptions = metadata.pop("descriptions", [])
        if not descriptions:
            return

        # in NMA, it is a list of description_type and description_text which has lang and value
        # in RDM, it is a list of description, type and lang

        converted_additional_descriptions = []
        for desc in descriptions:
            for desc_with_lang in desc.get("description_text", []):
                converted_desc = {
                    "description": desc_with_lang.get("value"),
                    "type": desc.get("description_type"),
                    "lang": desc_with_lang.get("lang"),
                }
                converted_additional_descriptions.append(converted_desc)

        metadata["additional_descriptions"] = converted_additional_descriptions

    def convert_metadata_identifiers(self, metadata: dict[str, Any]) -> None:
        """Convert identifiers from NMA format to RDM format."""
        identifiers = metadata.pop("identifiers", [])
        converted_identifiers = self.convert_identifiers(identifiers)
        if converted_identifiers:
            metadata["identifiers"] = converted_identifiers

    def convert_identifiers(self, identifiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert identifiers from NMA format to RDM format."""
        if not identifiers:
            return []

        # in NMA, it is a list of iri, value and scheme, scheme is a dictionary item with id
        # in RDM, it is a list of identifier (string), scheme (string), iri is not present
        # note: iri has been converted to the id and checked, so we know that the scheme exists

        converted_identifiers = []
        for ident in identifiers:
            converted_ident = {
                "identifier": ident.get("value"),
                "scheme": ident.get("scheme", {}).get("id"),
            }
            converted_identifiers.append(converted_ident)

        return converted_identifiers

    def convert_resource_type(self, metadata: dict[str, Any]) -> None:
        """Convert resource type from NMA format to RDM format."""
        resource_type = metadata.pop("resource_type", None)
        if resource_type is None:
            return

        # in NMA, it is a dictionary value with id and title
        # in RDM, it is a dictionary value with type and subtype

        # TODO: keep this RDM or use our hierarchical resource types?
        # for now, we keep our hierarchical resource types

        metadata["resource_type"] = resource_type

    def convert_publication_date(self, metadata: dict[str, Any]) -> None:
        """Convert publication date from NMA format to RDM format."""
        # in NMA, we have publication_year and time_reference with Issued
        # in RDM, we have a specialized publication_date field

        publication_year = metadata.pop("publication_year", None)
        created_date = next(
            (
                dt
                for dt in (
                    tr.get("temporal_representation", {}).get("time_instant")
                    for tr in metadata.get("time_references", [])
                    if tr.get("date_type", {}).get("id") == "Created"
                )
                if dt is not None
            ),
            None,
        )
        publication_date: str | None = None
        if created_date:
            date_value: str | None = created_date.get("date_time") or created_date.get("date")
            if date_value:
                publication_date = date_value.split("T")[0] if "T" in date_value else date_value
        elif publication_year is not None:
            publication_date = f"{publication_year}-01-01"

        if publication_date is not None:
            metadata["publication_date"] = publication_date

    def convert_publisher(
        self,
        metadata: dict[str, Any],
        qualified_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert publisher from NMA format to RDM format."""
        # in ccmm, publisher is represented as qualified relation with role with 'id': Publisher
        qualified_relations, selection = self.extract_qualified_relation(
            qualified_relations, lambda qr: qr.get("role", {}).get("id") == "Publisher"
        )
        if not selection:
            return qualified_relations

        # in RDM, publisher is a simple string field
        publishers = [x.get("person", None) or x.get("organization", None) for x in selection]
        publishers = [p for p in publishers if p is not None]
        publisher_names = [p.get("name") for p in publishers if p and p.get("name") is not None]
        if publisher_names:
            # take the first publisher only
            metadata["publisher"] = ", ".join(publisher_names)

        return qualified_relations

    def extract_qualified_relation(
        self,
        qualified_relations: list[dict[str, Any]],
        predicate: Callable[[dict[str, Any]], bool],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract a qualified relation from the list based on the predicate.

        Returns the modified list (with the extracted item removed) and the extracted items
        (or None if not found).
        """
        non_extracted_relations = []
        extracted_relations = []

        for qr in qualified_relations:
            if predicate(qr):
                extracted_relations.append(qr)
            else:
                non_extracted_relations.append(qr)
        return non_extracted_relations, extracted_relations

    def convert_creators(
        self,
        metadata: dict[str, Any],
        qualified_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert creators from NMA format to RDM format."""
        # in ccmm, creators are represented as qualified relations with role with 'id': Creator
        qualified_relations, selection = self.extract_qualified_relation(
            qualified_relations, lambda qr: qr.get("role", {}).get("id") == "Creator"
        )
        if not selection:
            return qualified_relations

        # in RDM, creators are a list of creators
        creators = [self.convert_qualified_relation_to_creatibutor(qr) for qr in selection]
        if creators:
            metadata["creators"] = creators

        return qualified_relations

    def convert_contributors(
        self,
        metadata: dict[str, Any],
        qualified_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert contributors from NMA format to RDM format."""
        # in ccmm, creators are represented as qualified relations with role with 'id': Creator
        qualified_relations, selection = self.extract_qualified_relation(
            qualified_relations,
            lambda qr: qr.get("role", {}).get("id") not in ("Creator", "Publisher"),
        )
        if not selection:
            return qualified_relations

        # in RDM, creators are a list of creators
        contributors = [self.convert_qualified_relation_to_creatibutor(qr) for qr in selection]
        if contributors:
            metadata["contributors"] = contributors

        return qualified_relations

    def convert_qualified_relation_to_creatibutor(
        self,
        qualified_relation: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert a qualified relation to a creator/contributor."""
        # in ccmm, this is an object with:
        #  - role: vocabulary
        #  - relation: choice of person or organization

        relation = qualified_relation["relation"]
        role = qualified_relation["role"]

        person = relation.get("person", None)
        organization = relation.get("organization", None)

        if person:
            person_or_org, affiliations = self.convert_person(person)
        elif organization:
            person_or_org = self.convert_organization(organization)
            affiliations = []
        else:
            raise ValueError("Qualified relation must have either person or organization.")

        ret = {
            "role": role,
            "person_or_org": person_or_org,
            "affiliations": affiliations,
        }
        return {k: v for k, v in ret.items() if v}

    def convert_person(
        self,
        person: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Convert a person to RDM format.

        Returns a tuple of person_or_org and affiliations.
        """
        person_or_org = {
            "name": person.get("name"),
            "type": "personal",
            "given_name": " ".join(person.get("given_names", [])),
            "family_name": " ".join(person.get("family_names", [])),
            "identifiers": self.convert_identifiers(person.get("identifiers", [])),
        }

        affiliations = []
        for aff in person.get("affiliations", []):
            identifiers = aff.get("identifiers", [])
            affiliation_id = self.get_affiliation_by_identifiers(identifiers)
            if affiliation_id is not None:
                affiliations.append(
                    {
                        "id": affiliation_id,
                        "name": aff.get("name"),
                    }
                )
            else:
                affiliations.append(
                    {
                        "name": aff.get("name"),
                    }
                )

        return person_or_org, affiliations

    def convert_organization(
        self,
        organization: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert an organization to RDM format."""
        return {
            "name": organization.get("name"),
            "type": "organizational",
            "identifiers": self.convert_identifiers(organization.get("identifiers", [])),
        }

    def get_affiliation_by_identifiers(
        self,
        _identifiers: list[dict[str, Any]],
    ) -> str | None:
        """Get affiliation id by identifiers."""
        log.error("Affiliation lookup by identifiers not implemented yet.")
        return None

    def convert_languages(self, metadata: dict[str, Any]) -> None:
        """Convert languages from NMA format to RDM format."""
        # in NMA, we have primary_language and other_languages
        # in RDM, languages are a list of vocabulary items

        primary_language = metadata.pop("primary_language", None)
        other_languages = metadata.pop("other_languages", [])

        langs = [primary_language, *other_languages] if primary_language else other_languages

        if langs:
            metadata["languages"] = langs

    def convert_subjects(self, metadata: dict[str, Any]) -> None:
        """Convert subjects from NMA format to RDM format."""
        # in NMA, subjects are a list of iri, classification_code, subject_scheme (vocabulary) and title
        # in RDM, it is optional id and string value

        subjects = metadata.pop("subjects", [])

        # as invenio ids for subjects must be unique accross subject schemes,
        # we can not map classification_code alone to id
        # what we do is to prepend the scheme id to the classification_code
        # to create a unique id

        converted_subjects = []
        for subj in subjects:
            classification_code = subj.get("classification_code")
            subject_scheme = subj.get("subject_scheme", {}).get("id")
            multilingual_title = subj.get("title", [])
            vocabulary_id = (
                f"{subject_scheme}:{classification_code}" if classification_code and subject_scheme else None
            )
            for translated_title in multilingual_title:
                converted_subj = (
                    {
                        "id": vocabulary_id,
                        "title": translated_title.get("value"),
                    }
                    if vocabulary_id
                    else {
                        "title": translated_title.get("value"),
                    }
                )
                converted_subjects.append(converted_subj)

        if subjects:
            metadata["subjects"] = subjects

    def convert_funding(self, metadata: dict[str, Any]) -> None:
        """Convert funding from NMA format to RDM format."""
        # in NMA, funding is a list of iri, award_title,
        # funders person_or_org, funding_program and local_identifier,
        # where funding_program is an IRI
        # in RDM, funding is a a list of funder (id and name)
        # and award, which has title, number, id and identifiers

        fundings = metadata.pop("funding_references", [])
        converted_fundings: list[dict[str, Any]] = []
        for fund in fundings:
            funders = fund.get("funders", [])
            converted_funders = []
            for funder in funders:
                organization = funder.get("organization", {})
                person = funder.get("person", {})
                if organization:
                    funder_name = organization.get("name")
                    funder_id = self.get_affiliation_by_identifiers(organization.get("identifiers", []))
                    converted_funders.append(
                        {
                            "id": funder_id,
                            "name": funder_name,
                        }
                        if funder_id
                        else {
                            "name": funder_name,
                        }
                    )
                elif person:
                    # not correct, will get errors later
                    # but user will know that something was wrong
                    converted_funders.append(person)
            award_title = fund.get("award_title")
            local_identifier = fund.get("local_identifier")
            award = {
                "title": award_title,
                "number": local_identifier,
            }
            converted_fundings.extend(
                {
                    "funder": f,
                    "award": award,
                }
                for f in converted_funders
            )
        if converted_fundings:
            metadata["funding"] = converted_fundings

    def convert_related_resources(self, metadata: dict[str, Any]) -> None:
        """Convert related resources from NMA format to nr-docs format.

        Currently this method is empty, we need to figure out
        if we want to do any conversion here.

        We can not use RDM as RDM has only related identifiers
        and we need more information here.
        """


class CCMMXMLProductionParser(CCMMXMLProductionParserBase, CCMMXMLNMAParser):
    """Parser for CCMM XML version 1.1.0 for production repository."""

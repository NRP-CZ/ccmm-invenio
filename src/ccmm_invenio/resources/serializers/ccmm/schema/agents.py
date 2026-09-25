#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm agents (persons, organizations) and their roles <-> RDM creators, contributors, publisher."""

from __future__ import annotations

from typing import Any, override

from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import EXCLUDE, Schema, ValidationError, fields, missing, post_dump, post_load, pre_load, validate
from marshmallow_utils.fields import SanitizedUnicode

from ccmm_invenio.resources.serializers.ccmm.schema.identifiers import IdentifierSchema, service_item_exists
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField

CCMM_ROLE_CREATOR = "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Creator"


CCMM_ROLE_PUBLISHER = "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Publisher"
"""The ccmm roles that map to invenio creators and publisher, any other role is a contributor."""


def _ccmm_role(iri: str) -> dict[str, Any]:
    """Role as a ccmm {iri, label} - the label from the role vocabulary with the iri among its mappings.

    A bare iri when the roles are not loaded (e.g. an OAI-PMH export without the fixtures).
    """
    for vocabulary_type in ("contributorsroles", "creatorsroles"):
        for hit in vocab_service.scan(
            system_identity,
            params={"type": vocabulary_type, "skos": [f"exactMatch:{iri}"]},  # list, the param interpreter iterates it
            type=vocabulary_type,
        ):
            return {
                "iri": iri,
                "label": [{"lang": lang, "$": text} for lang, text in (hit.get("title") or {}).items()],
            }
    return {"iri": iri}


class PersonOrOrgSchema(Schema):
    """CCMM agent (person or organization) <-> RDM person_or_org.

    Expects the agent with an added "type" (personal or organizational), see CreatibutorSchema.
    Types as in invenio_rdm_records.services.schemas.metadata.PersonOrOrganizationSchema.
    """

    class Meta:
        """Schema options."""

        # iri (0..1), alternate_name (0..n, organization), contact_point (0..n): no counterpart in invenio;
        # affiliation (person) is handled by CreatibutorSchema
        unknown = EXCLUDE

    type = fields.String(required=True, validate=validate.OneOf(["personal", "organizational"]))

    # ccmm 1..1
    name = SanitizedUnicode()

    # ccmm person 0..n each - joined by a space
    given_name = fields.Method(serialize="dump_given_name", deserialize="load_joined")
    family_name = fields.Method(serialize="dump_family_name", deserialize="load_joined")

    # ccmm 0..n
    identifiers = fields.Nested(IdentifierSchema, many=True, data_key="identifier")

    def load_joined(self, value: Any) -> str:
        """Join the ccmm names (a list) by a space."""
        return " ".join(value) if isinstance(value, list) else str(value)

    def dump_given_name(self, obj: dict[str, Any]) -> Any:
        """Dump as a list with a single name."""
        return [obj["given_name"]] if obj.get("given_name") else missing

    def dump_family_name(self, obj: dict[str, Any]) -> Any:
        """Dump as a list with a single name."""
        return [obj["family_name"]] if obj.get("family_name") else missing

    @post_load
    def family_name_from_name(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """RDM requires the family name of a person - take it from the name if missing ("Family, Given")."""
        if data["type"] == "personal" and not data.get("family_name") and data.get("name"):
            family_name, _, given_name = data["name"].partition(",")
            data["family_name"] = family_name.strip()
            if given_name.strip() and not data.get("given_name"):
                data["given_name"] = given_name.strip()
        return data


class AffiliationSchema(Schema):
    """CCMM organization (affiliation of a person) <-> RDM affiliation.

    The id is set when the ROR of the organization is in the affiliations vocabulary (its ids are ROR ids),
    other identifiers have no counterpart in RDM and are dropped. On dump, the id is the ROR identifier.
    Types as in invenio_vocabularies.contrib.affiliations.schema.AffiliationRelationSchema.
    """

    class Meta:
        """Schema options."""

        # iri (0..1), alternate_name (0..n), contact_point (0..n): no counterpart in invenio
        unknown = EXCLUDE

    # ccmm 1..1
    name = SanitizedUnicode(required=True)

    # ccmm 0..n; only to find the id (see affiliation_id)
    identifiers = fields.Nested(IdentifierSchema, many=True, data_key="identifier", load_only=True)

    @post_load
    def affiliation_id(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Set the id of the affiliation from its ROR, if it is in the affiliations vocabulary."""
        identifiers = data.pop("identifiers", [])
        ror = next((i["identifier"] for i in identifiers if i["scheme"] == "ror"), None)
        if ror and service_item_exists("affiliations", ror):
            return {"id": ror, **data}
        return data

    @post_dump(pass_original=True)
    def dump_ror(self, data: dict[str, Any], original: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Dump the id as the ROR identifier of the organization."""
        if original.get("id"):
            data["identifier"] = IdentifierSchema(many=True).dump([{"identifier": original["id"], "scheme": "ror"}])
        return data


class CreatibutorSchema(Schema):
    """CCMM qualified relation (an agent with a role) <-> RDM creator or contributor, without the role.

    The ccmm relation (an agent - {"person": {...}} or {"organization": {...}}) is split to person_or_org
    and the affiliations (of a person) on load and joined back on dump.
    Types as in invenio_rdm_records.services.schemas.metadata.CreatorSchema.
    """

    class Meta:
        """Schema options."""

        # iri (0..1): no counterpart in invenio
        unknown = EXCLUDE

    # ccmm relation 1..1, see unpack_relation
    person_or_org = fields.Nested(PersonOrOrgSchema, required=True)

    # ccmm relation/person/affiliation 0..n
    affiliations = fields.Nested(AffiliationSchema, many=True, data_key="affiliation")

    @pre_load
    def unpack_relation(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Split the ccmm agent to person_or_org (with the type) and affiliations."""
        data = dict(data)
        relation = data.pop("relation", None) or {}
        if "person" in relation:
            person = dict(relation["person"])
            if "affiliation" in person:
                data["affiliation"] = person.pop("affiliation")
            data["person_or_org"] = {**person, "type": "personal"}
        elif "organization" in relation:
            data["person_or_org"] = {**relation["organization"], "type": "organizational"}
        return data

    @post_dump
    def pack_relation(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Join person_or_org and affiliations back to the ccmm agent."""
        agent = data.pop("person_or_org")
        affiliations = data.pop("affiliation", None)
        if agent.pop("type") == "personal":
            data["relation"] = {"person": {**agent, **({"affiliation": affiliations} if affiliations else {})}}
        else:
            # ponytail: RDM allows affiliations of an organization, ccmm does not - they are dropped
            data["relation"] = {"organization": agent}
        return data


class CreatorSchema(CreatibutorSchema):
    """CCMM qualified relation with the Creator role <-> RDM creator.

    The ccmm role is always Creator - a role of the invenio creator (creatorsroles) is not dumped.
    """

    @post_dump
    def creator_role(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        """Add the ccmm Creator role."""
        return {**data, "role": _ccmm_role(CCMM_ROLE_CREATOR)}


class ContributorSchema(CreatibutorSchema):
    """CCMM qualified relation with any other role than Creator and Publisher <-> RDM contributor."""

    # ccmm 1..1
    role = CCMMVocabularyField("contributorsroles", required=True)


class PublisherField(fields.Field):
    """CCMM qualified relations with the Publisher role <-> RDM publisher (a string).

    The names of the publishers are joined by ", ", on dump the publisher is a single organization.
    """

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> Any:
        if not isinstance(value, list):
            raise ValidationError("Expected a list of qualified relations")
        agents: list[dict[str, Any]] = [next(iter(relation.get("relation", {}).values()), {}) for relation in value]
        return ", ".join(agent["name"] for agent in agents if agent.get("name")) or None

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if not value:
            return None
        return [{"relation": {"organization": {"name": value}}, "role": _ccmm_role(CCMM_ROLE_PUBLISHER)}]

#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Serializer converting a CCMM production Invenio record into CCMM XML.

``CCMMSerializer.serialize()`` is the (best-effort) inverse of
``ccmm_invenio.parsers.production_1_1_0.CCMMXMLProductionParser``: it takes a record
whose ``metadata`` follows ``schema.json`` and produces a CCMM ``<dataset>``
``lxml.etree`` element, following the ``dataset`` complex type of the merged CCMM XSD
(``ccmm_versions/merged/1.1.0-2026-01-29.xsd``, namespace
``https://schema.ccmm.cz/research-data/1.1``).

The parser's namespace (``https://schema.ccmm.cz/research-data/1.0``) is for an older
NMA XML feed and is unrelated to the namespace used here -- see ``ccmm_export_plan.md``.

This module is written top-down and one-method-per-XSD-element/type, mirroring the
structure of ``CCMMXMLNMAParser``/``CCMMXMLProductionParser`` in reverse, so that each
``serialize_*`` method can be checked directly against the XSD element/type it is named
after. Vocabulary-valued fields (JSON shape ``{"id": ..., "title": {...}, "@v": ...}``,
or occasionally a bare string id) are all funnelled through the single
``serialize_vocabulary`` method, identified by a `vocabulary_type` string picked
according to the calling context (mirrors ``register_vocabulary_parser``/
``VocabularyTag`` on the parsing side).

See ``ccmm_export_plan.md`` (repository root) for the full field-by-field mapping,
including every deliberately-dropped field and every ambiguous/lossy reverse mapping.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

import langcodes
from langcodes.tag_parser import LanguageTagError
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]

from ccmm_invenio.parsers.base import QualifiedTag, XMLNamespace

if TYPE_CHECKING:
    from invenio_rdm_records.records.api import RDMRecord
    from lxml.etree import _Element as Element
else:
    Element = Any

#: qualified name of the ``xml:lang`` attribute, used on every multilingual text element
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


class CCMMSerializer:
    """Serializes a CCMM production record's ``metadata`` into a CCMM ``<dataset>`` XML element."""

    #: namespace of the CCMM XSD this serializer targets (see module docstring)
    ns = XMLNamespace("https://schema.ccmm.cz/research-data/1.1")

    #
    # Public API
    #

    def serialize(self, record: RDMRecord) -> Element:
        """Serialize a full production record (an ``RDMRecord``) into a CCMM ``<dataset>`` element.

        `record` is the full record dict as stored by Invenio (``{"metadata": {...},
        ...}``); its ``metadata`` sub-dict follows the shape documented under
        ``properties.metadata`` in ``schema.json`` (the same shape
        ``CCMMXMLProductionParser.parse()`` returns as ``record["metadata"]``).
        """
        return self.serialize_dataset(record["metadata"])

    def serialize_dataset(self, metadata: dict[str, Any]) -> Element:
        """Serialize `metadata` into a ``<dataset>`` element, in the XSD's child order.

        ``metadata_identification``, ``distribution``, ``validation_result`` and
        ``provenance`` (all optional/unbounded in the XSD) are not emitted:
        ``CCMMXMLProductionParser.parse()`` already strips them for production records
        (see its handling of ``metadata_identifications``/``distributions``, and
        ``convert_provenances``/``convert_validation_results``), so there is no source
        data for them here either.
        """
        root = etree.Element(str(self.ns.dataset), nsmap={None: self.ns.uri})
        self._serialize_dataset_identification(root, metadata)
        self._serialize_dataset_content(root, metadata)
        return root

    def _serialize_dataset_identification(self, root: Element, metadata: dict[str, Any]) -> None:
        """Append the ``identifier``..``time_reference`` part of `dataset`'s child sequence to `root`."""
        for identifier in metadata.get("identifiers", []):
            root.append(self.serialize_identifier(identifier))

        self._append_text(root, self.ns.version, metadata.get("version"))
        self._append_text(root, self.ns.title, metadata.get("title"))

        for alternate_title in self.group_additional_titles(metadata):
            root.append(self.serialize_alternate_title(alternate_title))

        for relation in self.serialize_qualified_relations(metadata):
            root.append(relation)

        self._append_text(root, self.ns.publication_year, self.extract_publication_year(metadata))

        for time_reference in self.serialize_time_references(metadata):
            root.append(time_reference)

    def _serialize_dataset_content(self, root: Element, metadata: dict[str, Any]) -> None:
        """Append the ``resource_type``..``related_resource`` part of `dataset`'s child sequence to `root`."""
        self.serialize_vocabulary(root, self.ns.resource_type, "resourcetypes", metadata.get("resource_type"))

        primary_language, other_languages = self.split_languages(metadata.get("languages", []))
        self.serialize_vocabulary(root, self.ns.primary_language, "languages", primary_language)
        for other_language in other_languages:
            self.serialize_vocabulary(root, self.ns.other_language, "languages", other_language)

        terms_of_use = self.serialize_terms_of_use(metadata)
        if terms_of_use is not None:
            root.append(terms_of_use)

        for subject in self.group_subjects(metadata):
            root.append(self.serialize_subject(subject))

        for description in self.serialize_descriptions(metadata):
            root.append(description)

        for feature in metadata.get("locations", {}).get("features", []):
            root.append(self.serialize_location(feature))

        for funding_group in self.group_funding(metadata):
            root.append(self.serialize_funding_reference(funding_group))

        for related_resource in self.serialize_related_resources(metadata):
            root.append(related_resource)

    #
    # Small generic helpers
    #

    def _append_text(self, parent: Element, tag: QualifiedTag, value: str | None) -> Element | None:
        """Append ``<tag>value</tag>`` to `parent` if `value` is truthy; return the created element (or ``None``)."""
        if not value:
            return None
        el = etree.SubElement(parent, str(tag))
        el.text = str(value)
        return el

    def _append_i18n_text(
        self,
        parent: Element,
        tag: QualifiedTag,
        lang: str | None,
        value: str | None,
    ) -> Element | None:
        """Append ``<tag xml:lang="lang">value</tag>`` to `parent` if `value` is truthy.

        `lang` defaults to ``"und"`` (undetermined, mirrors ``parse_i18ndict_content``)
        when not known -- the XSD marks ``xml:lang`` as required on these elements.
        """
        if not value:
            return None
        el = etree.SubElement(parent, str(tag))
        el.text = str(value)
        el.set(XML_LANG, lang or "und")
        return el

    def _group_by_type(self, entries: list[dict[str, Any]], text_key: str) -> list[dict[str, Any]]:
        """Group a flat multilingual list (``additional_titles``/``additional_descriptions`` shape) by `type`.

        Both fields flatten one CCMM element with N ``xml:lang`` children into N JSON
        entries that each carry the *same* `type` (see ``convert_additional_titles`` /
        ``convert_additional_descriptions``); this regroups them, preserving order of
        first appearance of both groups and languages within a group. `type` is
        compared by its vocabulary ``id`` (falling back to the raw value, or ``None``).
        `lang` is converted from a CCMM language id to a BCP 47 tag here, once, since
        both callers (``additional_titles``/``additional_descriptions``) carry the same
        CCMM-language-id shape -- see ``xml_lang_from_ccmm_lang``.
        """
        groups: dict[Any, dict[str, Any]] = {}
        order: list[Any] = []
        for entry in entries:
            entry_type = entry.get("type")
            key = entry_type.get("id") if isinstance(entry_type, dict) else entry_type
            if key not in groups:
                groups[key] = {"type": entry_type, "items": []}
                order.append(key)
            lang = self.xml_lang_from_ccmm_lang((entry.get("lang") or {}).get("id"))
            groups[key]["items"].append({"lang": lang, "value": entry.get(text_key)})
        return [groups[key] for key in order]

    #
    # identifier / identifier_scheme
    #

    def serialize_identifier(self, entry: dict[str, Any]) -> Element:
        """Serialize ``{"identifier": ..., "scheme": ...}`` into an ``identifier`` element.

        ``scheme`` here is a bare vocabulary id string, not the usual
        ``{"id", "title", "@v"}`` shape (see ``convert_identifiers``, which discards
        everything but the id on the way in) -- ``serialize_vocabulary`` normalizes a
        bare string into ``{"id": value}``.
        """
        el = etree.Element(str(self.ns.identifier))
        self._append_text(el, self.ns.value, entry.get("identifier"))
        self.serialize_vocabulary(el, self.ns.scheme, "identifierschemes", entry.get("scheme"))
        return el

    #
    # alternate_title (from additional_titles[])
    #

    def group_additional_titles(self, container: dict[str, Any]) -> list[dict[str, Any]]:
        """Group `container`'s flat ``additional_titles[]`` list into per-type groups.

        Used both for the dataset-level ``additional_titles`` and for the same-shaped
        field on each ``related_resources[]`` entry.
        """
        return self._group_by_type(container.get("additional_titles", []), text_key="title")

    def serialize_alternate_title(self, group: dict[str, Any]) -> Element:
        """Serialize one group from ``group_additional_titles`` into an ``alternate_title`` element."""
        el = etree.Element(str(self.ns.alternate_title))
        for item in group["items"]:
            self._append_i18n_text(el, self.ns.title, item["lang"], item["value"])
        self.serialize_vocabulary(el, self.ns.alternate_title_type, "titletypes", group.get("type"))
        return el

    #
    # description (from the single "description" field and from additional_descriptions[])
    #

    def serialize_descriptions(self, metadata: dict[str, Any]) -> list[Element]:
        """Build all ``description[]`` elements for the dataset: the main description, then the additional ones.

        ``description`` (singular, a plain string) is the RDM "main abstract" field;
        CCMM has no distinguished slot for it (only a repeatable, typed
        ``description``), so it is emitted as one ``<description>`` with no
        ``description_type``. It is never produced by ``CCMMXMLProductionParser`` on
        the way in, so this is speculative. # TODO: check the implementation.
        """
        descriptions = []
        main_description = metadata.get("description")
        if main_description:
            descriptions.append(
                self.serialize_description({"type": None, "items": [{"lang": None, "value": main_description}]})
            )
        descriptions.extend(
            self.serialize_description(group)
            for group in self._group_by_type(metadata.get("additional_descriptions", []), text_key="description")
        )
        return descriptions

    def serialize_description(self, group: dict[str, Any]) -> Element:
        """Serialize one description group (see ``serialize_descriptions``) into a ``description`` element."""
        el = etree.Element(str(self.ns.description))
        for item in group["items"]:
            self._append_i18n_text(el, self.ns.description_text, item["lang"], item["value"])
        self.serialize_vocabulary(el, self.ns.description_type, "descriptiontypes", group.get("type"))
        return el

    #
    # resource_to_agent_relationship / agent (person | organization), from creators[]/contributors[]
    #

    def serialize_qualified_relations(self, container: dict[str, Any]) -> list[Element]:
        """Build ``qualified_relation[]`` from `container`'s ``creators[]`` then ``contributors[]``.

        A creator with no explicit ``role`` defaults to ``{"id": "Creator"}``, mirroring
        the predicate ``convert_creators`` uses to select creators out of
        ``qualified_relations`` on the way in. Contributors always carry an explicit
        role in the JSON and are passed through unchanged.
        """
        relations = [
            self.serialize_resource_to_agent_relationship(creator, creator.get("role") or {"id": "Creator"})
            for creator in container.get("creators", [])
        ]
        relations += [
            self.serialize_resource_to_agent_relationship(contributor, contributor.get("role"))
            for contributor in container.get("contributors", [])
        ]
        return relations

    def serialize_resource_to_agent_relationship(
        self,
        entry: dict[str, Any],
        role: dict[str, Any] | str | None,
    ) -> Element:
        """Serialize one creator/contributor dict into a ``qualified_relation`` (``resource_to_agent_relationship``)."""
        el = etree.Element(str(self.ns.qualified_relation))
        relation = etree.SubElement(el, str(self.ns.relation))
        person_or_org = entry.get("person_or_org") or {}
        # TODO: check the implementation -- `type` missing/unrecognized defaults to
        # "personal", mirroring `convert_person` always being the assumed shape unless
        # `organization` was set on the way in.
        if person_or_org.get("type") == "organizational":
            relation.append(self.serialize_organization(person_or_org))
            # NOTE: unlike `person`, the CCMM `organization` type has no `affiliation`
            # slot, so `entry["affiliations"]` has nowhere to go when the agent itself
            # is an organization -- dropped.
        else:
            relation.append(self.serialize_person(person_or_org, entry.get("affiliations", [])))
        self.serialize_vocabulary(el, self.ns.role, "resourceagentroletypes", role)
        return el

    def serialize_person(self, person: dict[str, Any], affiliations: list[dict[str, Any]] | None = None) -> Element:
        """Serialize a `person_or_org` dict (``type == "personal"``) into a ``person`` element.

        ``given_name``/``family_name`` are single space-joined strings on the way in
        (``CCMMXMLProductionParser.convert_person``: ``" ".join(person["given_names"])``);
        reversed here by splitting on whitespace back into repeated elements, which is
        lossy/ambiguous for a name part that legitimately contains a space.
        # TODO: check the implementation.
        """
        el = etree.Element(str(self.ns.person))
        for identifier in person.get("identifiers", []):
            el.append(self.serialize_identifier(identifier))
        self._append_text(el, self.ns.name, person.get("name"))
        for given_name in (person.get("given_name") or "").split():
            self._append_text(el, self.ns.given_name, given_name)
        for family_name in (person.get("family_name") or "").split():
            self._append_text(el, self.ns.family_name, family_name)
        for affiliation in affiliations or []:
            # `person/affiliation` shares `organization`'s content model but is locally
            # named `affiliation`, not `organization` -- rename the built element.
            affiliation_el = self.serialize_organization(affiliation)
            affiliation_el.tag = str(self.ns.affiliation)
            el.append(affiliation_el)
        return el

    def serialize_organization(self, organization: dict[str, Any]) -> Element:
        """Serialize an organization / affiliation / funder dict into an ``organization`` element.

        Used for ``person_or_org`` (when ``type == "organizational"``), for
        ``affiliations[]`` entries, and for ``funding[].funder`` (see
        ``serialize_agent_as_organization``) -- all three share the ``{"name",
        "identifiers"?}`` shape.
        """
        el = etree.Element(str(self.ns.organization))
        for identifier in organization.get("identifiers", []):
            el.append(self.serialize_identifier(identifier))
        self._append_text(el, self.ns.name, organization.get("name"))
        if organization.get("id") or organization.get("@v"):
            # TODO: check the implementation. A resolved-affiliation vocabulary id here
            # would need a reverse lookup back to a CCMM identifier; the forward
            # direction (`get_affiliation_by_identifiers`) is itself unimplemented, so
            # there is no confirmed shape to reverse. Currently dropped.
            pass
        return el

    #
    # publication_year / time_reference (from publication_date and dates[])
    #

    def extract_publication_year(self, metadata: dict[str, Any]) -> str | None:
        """Extract the ``xs:gYear`` CCMM requires (``dataset/publication_year``) from ``publication_date``."""
        publication_date = metadata.get("publication_date")
        if not publication_date:
            return None
        return str(publication_date)[:4]

    def serialize_time_references(self, metadata: dict[str, Any]) -> list[Element]:
        """Build ``time_reference[]`` from ``dates[]``, synthesizing one from ``publication_date`` if needed.

        CCMM requires at least one ``time_reference``. On the way in,
        ``convert_publication_date`` derives ``publication_date`` from a ``dates[]``
        entry typed ``Created`` when one exists, or from ``publication_year`` (as
        ``"{year}-01-01"``) otherwise; this mirrors that by only synthesizing a
        ``Created`` entry when ``dates[]`` doesn't already have one.
        # TODO: check the implementation -- see ccmm_export_plan.md.
        """
        dates = metadata.get("dates", [])
        time_references = [self.serialize_time_reference_from_date(date_entry) for date_entry in dates]
        has_created = any((date_entry.get("type") or {}).get("id") == "Created" for date_entry in dates)
        publication_date = metadata.get("publication_date")
        if not has_created and publication_date:
            time_references.append(
                self.serialize_time_reference_from_date({"date": publication_date, "type": {"id": "Created"}})
            )
        return time_references

    def serialize_time_reference_from_date(self, date_entry: dict[str, Any]) -> Element:
        """Serialize one ``dates[]`` entry into a ``time_reference`` element.

        Always built as a ``time_instant`` (never a ``time_interval``) -- schema.json's
        ``dates[].date`` only ever carries a single value, never a range.
        # TODO: check the implementation -- ``dates[].date`` may be a bare year (e.g.
        ``"2024"``), which is not a valid ``xs:date`` (requires ``YYYY-MM-DD``); it is
        passed through as-is here.
        """
        el = etree.Element(str(self.ns.time_reference))
        temporal_representation = etree.SubElement(el, str(self.ns.temporal_representation))
        time_instant = etree.SubElement(temporal_representation, str(self.ns.time_instant))
        self._append_text(time_instant, self.ns.date, date_entry.get("date"))
        self.serialize_vocabulary(el, self.ns.date_type, "datetypes", date_entry.get("type"))
        self._append_i18n_text(el, self.ns.date_information, "und", date_entry.get("description"))
        return el

    #
    # language_system (from languages[])
    #

    def split_languages(
        self,
        languages: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Split the flat ``languages[]`` list into ``(primary_language, other_languages)``.

        ``convert_languages`` flattens ``primary_language`` + ``other_languages`` into
        one list with the primary first (when set); this treats the first entry as
        primary and the rest as "other". Ambiguous when the original record had no
        ``primary_language`` at all -- the first ``other_language`` would incorrectly
        become ``primary_language`` here. # TODO: check the implementation.
        """
        if not languages:
            return None, []
        return languages[0], languages[1:]

    #
    # terms_of_use / license (from rights[])
    #

    def serialize_terms_of_use(self, metadata: dict[str, Any]) -> Element | None:
        """Serialize ``rights[]`` into a ``terms_of_use`` element, or ``None`` if `rights` is empty.

        ``terms_of_use.license`` is singular in CCMM; only ``rights[0]`` is used
        (mirrors ``convert_terms_of_use``, which always produces exactly one
        ``rights[]`` entry on the way in). Additional entries are dropped -- there is no
        CCMM slot for more than one license per dataset. ``rights[0].description`` maps
        onto ``terms_of_use``'s own (license-independent) ``description[]``.

        ``terms_of_use.access_rights`` is *required* by the XSD but has no source field
        in schema.json (access rights live outside ``metadata`` on real RDM records,
        under ``record.access``). # TODO: check the implementation.
        """
        rights = metadata.get("rights") or []
        if not rights:
            return None
        el = etree.Element(str(self.ns.terms_of_use))
        self.serialize_vocabulary(el, self.ns.access_rights, "accessrights", None)
        right = rights[0]
        if right.get("id"):
            self.serialize_vocabulary(el, self.ns.license, "licenses", right)
        else:
            el.append(self.serialize_license_document(right))
        for lang, text in (right.get("description") or {}).items():
            self._append_i18n_text(el, self.ns.description, lang, text)
        return el

    def serialize_license_document(self, right: dict[str, Any]) -> Element:
        """Serialize a *raw* (non-vocabulary) ``rights[]`` entry into a ``license`` (``license_document``) element.

        Only used when `right` has no resolved vocabulary ``id`` -- the fallback branch
        of ``convert_terms_of_use`` (``{"link": iri, "title": {lang: label}}``). ``icon``
        and ``props`` have no corresponding CCMM field and are dropped.
        """
        el = etree.Element(str(self.ns.license))
        self._append_text(el, self.ns.iri, right.get("link"))
        for lang, text in (right.get("title") or {}).items():
            self._append_i18n_text(el, self.ns.label, lang, text)
        return el

    #
    # subject (from subjects[])
    #

    def group_subjects(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Group the flat ``subjects[]`` list back into one group per distinct ``id``.

        ``id`` is ``"<subject_scheme_id>:<classification_code>"`` (see
        ``convert_subjects``); entries without an ``id`` are never grouped with each
        other, mirroring the per-language flattening loop
        (``for translated_title in multilingual_title: ...``) that produces one JSON
        entry per language of one CCMM subject.
        """
        groups: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        ungrouped: list[dict[str, Any]] = []
        for entry in metadata.get("subjects", []):
            subject_id = entry.get("id")
            if not subject_id:
                ungrouped.append({"id": None, "items": [{"lang": None, "value": entry.get("subject")}]})
                continue
            if subject_id not in groups:
                groups[subject_id] = {"id": subject_id, "items": []}
                order.append(subject_id)
            groups[subject_id]["items"].append({"lang": None, "value": entry.get("subject")})
        return [groups[key] for key in order] + ungrouped

    def serialize_subject(self, group: dict[str, Any]) -> Element:
        """Serialize one group from ``group_subjects`` into a ``subject`` element.

        ``id`` (``"<scheme>:<code>"``) is split back into ``subject_scheme`` and
        ``classification_code``. # TODO: check the implementation -- splitting on the
        first ``:`` is a heuristic; a scheme id or code containing ``:`` would break it.
        """
        el = etree.Element(str(self.ns.subject))
        for item in group["items"]:
            self._append_i18n_text(el, self.ns.title, item["lang"], item["value"])
        subject_id = group.get("id")
        if subject_id and ":" in subject_id:
            scheme_id, _, code = subject_id.partition(":")
            self._append_text(el, self.ns.classification_code, code)
            self.serialize_vocabulary(el, self.ns.subject_scheme, "subjectschemes", scheme_id)
        return el

    #
    # location (from locations.features[])
    #

    def serialize_location(self, feature: dict[str, Any]) -> Element:
        """Serialize one ``locations.features[]`` entry into a ``location`` element.

        See ccmm_export_plan.md, "Locations", for the (lossy) reverse mapping of
        ``identifiers[]``/``description`` -- both are repurposed fields on the way in
        (``convert_locations``), not literal CCMM identifiers/relation types.
        """
        el = etree.Element(str(self.ns.location))
        self._append_text(el, self.ns.name, feature.get("place"))
        geometry = feature.get("geometry")
        if geometry:
            el.append(self.serialize_geometry(geometry))
        for identifier in feature.get("identifiers", []):
            el.append(self.serialize_related_object_from_identifier(identifier))
        # `relation_type` is required by the XSD; `feature["description"]` is the only
        # candidate source (see convert_locations: `converted_feature["description"] =
        # relation_type["id"]`), wrapped as `{"id": ...}` for the vocabulary stub.
        # TODO: check the implementation.
        self.serialize_vocabulary(el, self.ns.relation_type, "locationrelationtypes", feature.get("description"))
        return el

    def serialize_related_object_from_identifier(self, identifier: dict[str, Any]) -> Element:
        """Serialize one location ``identifiers[]`` entry into a ``related_object`` (``related_resource``) element.

        Only ``{"scheme": "iri", "identifier": ...}`` is known to occur (the only shape
        ``convert_locations`` produces, taken from a related object's ``iri``);
        anything else falls back to a generic ``<identifier>`` child.
        # TODO: check the implementation.
        """
        el = etree.Element(str(self.ns.related_object))
        if identifier.get("scheme") == "iri":
            self._append_text(el, self.ns.iri, identifier.get("identifier"))
        else:
            el.append(self.serialize_identifier(identifier))
        return el

    def serialize_geometry(self, geometry: dict[str, Any]) -> Element:
        """Serialize a GeoJSON-ish ``{"type", "coordinates"}`` dict into a ``geometry`` element with a WKT literal.

        CCMM can also represent geometry as GML (``gml:AbstractGeometry``); we always
        emit WKT instead, which is simpler and sufficient for the ``Point``/``Polygon``
        shapes ``convert_locations`` actually produces.
        """
        el = etree.Element(str(self.ns.geometry))
        wkt = self._geojson_to_wkt(geometry)
        if wkt:
            self._append_text(el, self.ns.wkt, wkt)
        return el

    def _geojson_to_wkt(self, geometry: dict[str, Any]) -> str | None:
        """Convert a ``Point``/``Polygon`` GeoJSON-ish dict to a WKT literal string.

        Not a general GeoJSON->WKT converter -- only the two shapes
        ``convert_locations`` can produce (a plain ``Point``/``Polygon``, or a
        rectangular ``Polygon`` built from a bounding box) are handled.
        # TODO: check the implementation.
        """
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if not coordinates:
            return None
        if geometry_type == "Point":
            x, y = coordinates
            return f"POINT ({x} {y})"
        if geometry_type == "Polygon":
            rings = ", ".join("(" + ", ".join(f"{x} {y}" for x, y in ring) + ")" for ring in coordinates)
            return f"POLYGON ({rings})"
        return None

    #
    # funding_reference (from funding[])
    #

    def group_funding(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Group the flat ``funding[]`` list back into one group per distinct award.

        ``convert_funding`` explodes one CCMM ``funding_reference`` with N funders into
        N JSON entries that each duplicate the same ``award``
        (``converted_fundings.extend({"funder": f, "award": award} for f in
        converted_funders)``); this regroups entries sharing the same
        ``(award.title, award.number)`` back into one ``funding_reference`` with
        multiple ``<funder>`` children. # TODO: check the implementation.
        """
        groups: dict[Any, dict[str, Any]] = {}
        order: list[Any] = []
        for entry in metadata.get("funding", []):
            award = entry.get("award") or {}
            key = (tuple(sorted((award.get("title") or {}).items())), award.get("number"))
            if key not in groups:
                groups[key] = {"award": award, "funders": []}
                order.append(key)
            funder = entry.get("funder")
            if funder:
                groups[key]["funders"].append(funder)
        return [groups[key] for key in order]

    def serialize_funding_reference(self, group: dict[str, Any]) -> Element:
        """Serialize one group from ``group_funding`` into a ``funding_reference`` element."""
        el = etree.Element(str(self.ns.funding_reference))
        award = group["award"]
        self._append_text(el, self.ns.local_identifier, award.get("number"))
        title_values = list((award.get("title") or {}).values())
        self._append_text(el, self.ns.award_title, title_values[0] if title_values else None)
        # `award.program` is never populated by `convert_funding` on the way in, so
        # there is no confirmed evidence that it should map to `funding_program` (an
        # `xs:anyURI`) -- best-effort guess. # TODO: check the implementation.
        self._append_text(el, self.ns.funding_program, award.get("program"))
        for funder in group["funders"]:
            # `funder` is `ccmm:agent` (a choice of organization|person), so -- unlike
            # `affiliation` above -- it needs an extra wrapping element, the same way
            # `resource_to_agent_relationship/relation` wraps its `organization`/`person`.
            funder_el = etree.SubElement(el, str(self.ns.funder))
            funder_el.append(self.serialize_agent_as_organization(funder))
        return el

    def serialize_agent_as_organization(self, funder: dict[str, Any]) -> Element:
        """Serialize a ``funding[].funder`` dict into a ``funder`` (``agent`` choice) element.

        Always emitted as ``<organization>``: the RDM ``funder`` shape (``{"name",
        "id"?}``) carries no ``type`` discriminator, and ``convert_funding``'s handling
        of person funders is itself marked broken on the way in (``# not correct, will
        get errors later``), so there is nothing reliable to reverse for that case.
        # TODO: check the implementation.
        """
        return self.serialize_organization(funder)

    #
    # related_resource (from related_resources[] and related_identifiers[])
    #

    def serialize_related_resources(self, metadata: dict[str, Any]) -> list[Element]:
        """Build all ``related_resource[]``: rich ``related_resources[]``, then plain ``related_identifiers[]``."""
        resources = [self.serialize_related_resource(entry) for entry in metadata.get("related_resources", [])]
        resources += [
            self.serialize_related_resource_from_identifier(entry) for entry in metadata.get("related_identifiers", [])
        ]
        return resources

    def serialize_related_resource(self, entry: dict[str, Any]) -> Element:
        """Serialize one ``related_resources[]`` entry into a ``related_resource`` element.

        Only fields with a corresponding CCMM ``related_resource`` slot are emitted:
        ``identifiers`` -> ``identifier[]``, ``title``, ``additional_titles`` ->
        ``alternate_title[]``, ``creators``/``contributors`` -> ``qualified_relation[]``,
        ``dates`` -> ``time_reference[]``, ``resource_type``, ``relation_type`` ->
        ``resource_relation_type``.

        ``publisher``, ``publication_date``, ``subjects``, ``funding``, ``rights``,
        ``languages``, ``locations``, ``additional_descriptions`` and ``imported_from``
        have **no** corresponding field on the CCMM ``related_resource`` type (checked
        against the XSD) and are intentionally dropped -- see ccmm_export_plan.md.
        """
        el = etree.Element(str(self.ns.related_resource))
        for identifier in entry.get("identifiers", []):
            el.append(self.serialize_identifier(identifier))
        self._append_text(el, self.ns.title, entry.get("title"))
        for alternate_title in self.group_additional_titles(entry):
            el.append(self.serialize_alternate_title(alternate_title))
        for relation in self.serialize_qualified_relations(entry):
            el.append(relation)
        for date_entry in entry.get("dates", []):
            el.append(self.serialize_time_reference_from_date(date_entry))
        self.serialize_vocabulary(el, self.ns.resource_type, "resourcetypes", entry.get("resource_type"))
        self.serialize_vocabulary(
            el, self.ns.resource_relation_type, "resourcerelationtypes", entry.get("relation_type")
        )
        return el

    def serialize_related_resource_from_identifier(self, entry: dict[str, Any]) -> Element:
        """Serialize one ``related_identifiers[]`` entry into a minimal ``related_resource`` element.

        ``related_identifiers`` is a native RDM field with no dedicated CCMM type and no
        forward converter in ``CCMMXMLProductionParser`` to check this against; mapped
        onto the identifier/relation_type/resource_type subset of ``related_resource``
        (no title, no creators -- schema.json carries none for this field).
        # TODO: check the implementation -- this mapping direction is unverified.
        """
        el = etree.Element(str(self.ns.related_resource))
        el.append(self.serialize_identifier({"identifier": entry.get("identifier"), "scheme": entry.get("scheme")}))
        self.serialize_vocabulary(el, self.ns.resource_type, "resourcetypes", entry.get("resource_type"))
        self.serialize_vocabulary(
            el, self.ns.resource_relation_type, "resourcerelationtypes", entry.get("relation_type")
        )
        return el

    #
    # Vocabulary stub -- shared by every vocabulary-valued field above
    #

    def serialize_vocabulary(
        self,
        parent: Element,
        tag: QualifiedTag,
        vocabulary_type: str,
        value: dict[str, Any] | str | None,
    ) -> Element | None:
        """Serialize a vocabulary-referencing `value` into a ``<tag>`` element under `parent`.

        `value` is normally ``{"id": ..., "title": {...}, "@v": ...}`` but for a few
        fields (e.g. ``identifiers[].scheme``) it is a bare string id, normalized to
        ``{"id": value}`` below. Does nothing (returns ``None``) if `value` is falsy.
        """
        if not value:
            return None
        if isinstance(value, str):
            value = {"id": value}

        iri = f"https://nma.eosc.cz/vocabularies/{vocabulary_type}/{value['id']}"

        el = etree.SubElement(parent, str(tag))
        etree.SubElement(el, str(self.ns.iri)).text = iri
        return el

    @staticmethod
    @functools.lru_cache(maxsize=16)
    def xml_lang_from_ccmm_lang(lang: str | None) -> str:
        """Convert a CCMM language vocabulary id into the BCP 47 tag ``xml:lang`` expects.

        CCMM languages (``additional_titles[].lang.id``, ``additional_descriptions[].lang.id``)
        are uppercase ISO 639-2 alpha-3 codes (e.g. ``"ENG"``, ``"CES"``) -- the reverse of what
        ``CCMMXMLProductionParser.lang2_to_lang3`` produces when parsing. ``xml:lang`` instead
        expects a BCP 47 tag (e.g. ``"en"``, ``"cs"``); `langcodes` handles both the terminology
        and bibliographic ISO 639-2 variants (``"CES"``/``"CZE"`` both resolve to ``"cs"``).

        Returns ``"unk"`` (ISO 639-3 for "Unknown language") if `lang` is falsy or not a
        recognized language code -- never ``None``, since ``xml:lang`` is required on every
        element this feeds into. A ``staticmethod`` (rather than a bound method) so
        ``lru_cache`` caches on `lang` alone and doesn't pin `self` in memory.
        """
        if not lang:
            return "unk"
        try:
            language = langcodes.Language.get(lang)
        except LanguageTagError:
            return "unk"
        if not language.is_valid() or not language.language:
            return "unk"
        return str(language)

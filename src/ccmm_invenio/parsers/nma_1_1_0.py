#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Parser for CCMM XML version 1.1.0 for NMA."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from .base import CCMMXMLParser, QualifiedTag, VocabularyLoader, XMLNamespace, datatype_parser

if TYPE_CHECKING:
    from lxml.etree import _Element as Element


class CCMMXMLNMAParser(CCMMXMLParser):
    """Parser for CCMM XML version 1.1.0 for NMA."""

    # ccmm namespace
    ns = XMLNamespace("https://schema.ccmm.cz/research-data/1.0")
    gml = XMLNamespace("http://www.opengis.net/gml/3.2")

    def __init__(self, vocabulary_loader: VocabularyLoader):
        """Initialize the parser with the given vocabulary loader."""
        super().__init__(vocabulary_loader)

        self.titletypes_parser = self.register_vocabulary_parser("titletypes")
        self.descriptiontypes_parser = self.register_vocabulary_parser("descriptiontypes")
        self.identifierschemes_parser = self.register_vocabulary_parser("identifierschemes")
        self.languages_parser = self.register_vocabulary_parser("languages")
        self.resourcetypes_parser = self.register_vocabulary_parser("resourcetypes")
        self.datetypes_parser = self.register_vocabulary_parser("datetypes")
        self.accessrights_parser = self.register_vocabulary_parser("accessrights")
        self.license_parser = self.register_vocabulary_parser("licenses")
        self.resourcerelationtypes_parser = self.register_vocabulary_parser("resourcerelationtypes")
        self.checksumalgorithms_parser = self.register_vocabulary_parser("checksumalgorithms")
        self.fileformats_parser = self.register_vocabulary_parser("fileformats")
        self.mediatypes_parser = self.register_vocabulary_parser("mediatypes")
        self.locationrelationtypes_parser = self.register_vocabulary_parser("locationrelationtypes")
        self.resourceagentroletypes_parser = self.register_vocabulary_parser("resourceagentroletypes")
        self.subjectschemes_parser = self.register_vocabulary_parser("subjectschemes")

    @override
    def parse(self, xml_root: Element) -> dict[str, Any]:
        """Parse the root element of the CCMM XML record."""
        record: dict[str, Any] = {}

        record["metadata"] = self.parse_ccmmdataset(xml_root, [])
        return record

    @datatype_parser()
    def parse_ccmmaddress(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type address to CCMMAddress."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "address_areas": self.parse_text_field(
                self.ns.address_area,
                children,
                path,
                cardinality="optional_array",
            ),
            "administrative_unit_level_1s": self.parse_text_field(
                self.ns.administrative_unit_level_1,
                children,
                path,
                cardinality="optional_array",
            ),
            "administrative_unit_level_2s": self.parse_text_field(
                self.ns.administrative_unit_level_2,
                children,
                path,
                cardinality="optional_array",
            ),
            "full_addresses": self.parse_text_field(
                self.ns.full_address,
                children,
                path,
                cardinality="optional_array",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
            "locator_designators": self.parse_text_field(
                self.ns.locator_designator,
                children,
                path,
                cardinality="optional_array",
            ),
            "locator_names": self.parse_text_field(
                self.ns.locator_name,
                children,
                path,
                cardinality="optional_array",
            ),
            "po_boxes": self.parse_text_field(
                self.ns.po_box,
                children,
                path,
                cardinality="optional_array",
            ),
            "post_codes": self.parse_text_field(
                self.ns.post_code,
                children,
                path,
                cardinality="optional_array",
            ),
            "post_names": self.parse_text_field(
                self.ns.post_name,
                children,
                path,
                cardinality="optional_array",
            ),
            "thoroughfares": self.parse_text_field(
                self.ns.thoroughfare,
                children,
                path,
                cardinality="optional_array",
            ),
        }

    @datatype_parser()
    def parse_ccmmagent(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type agent to CCMMAgent."""
        children = self.children(el)
        return {
            "organization": self.parse_field(
                self.ns.organization,
                children,
                path,
                cardinality="optional",
                datatype="ccmmorganization",
            ),
            "person": self.parse_field(
                self.ns.person,
                children,
                path,
                cardinality="optional",
                datatype="ccmmperson",
            ),
        }

    @datatype_parser()
    def parse_ccmmalternatetitle(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type alternate_title to CCMMAlternateTitle."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "alternate_title_type": self.titletypes_parser.parse_field(
                self.ns.alternate_title_type,
                children,
                path,
                cardinality="optional",
            ),
            "title": self.parse_multilingual(
                self.ns.title,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmapplicationprofile(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type application_profile to CCMMApplicationProfile."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmchecksum(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type checksum to CCMMChecksum."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "algorithm": self.parse_text_field(
                self.ns.algorithm,
                children,
                path,
                cardinality="optional",
            ),
            "checksum_value": self.parse_text_field(
                self.ns.checksum_value,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmcontactdetails(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type contact_details to CCMMContactDetails."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "addresses": self.parse_field(
                self.ns.address,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmaddress",
            ),
            "dataBoxes": self.parse_text_field(
                self.ns.data_box,
                children,
                path,
                cardinality="optional_array",
            ),
            "emails": self.parse_text_field(
                self.ns.email,
                children,
                path,
                cardinality="optional_array",
            ),
            "phones": self.parse_text_field(
                self.ns.phone,
                children,
                path,
                cardinality="optional_array",
            ),
        }

    @datatype_parser()
    def parse_ccmmdataservice(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type data_service to CCMMDataService."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "endpoint_urls": self.parse_field(
                self.ns.endpoint_url,
                children,
                path,
                cardinality="array",
                datatype="ccmmresource",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmdataset(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type data_set to CCMMDataSet."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "alternate_titles": self.parse_field(
                self.ns.alternate_title,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmalternatetitle",
            ),
            "descriptions": self.parse_field(
                self.ns.description,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmdescription",
            ),
            "distributions": self.parse_field(
                self.ns.distribution,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmdistribution",
            ),
            "funding_references": self.parse_field(
                self.ns.funding_reference,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmfundingreference",
            ),
            "identifiers": self.parse_field(
                self.ns.identifier,
                children,
                path,
                cardinality="array",
                datatype="ccmmidentifier",
            ),
            "locations": self.parse_field(
                self.ns.location,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmlocation",
            ),
            "metadata_identifications": self.parse_field(
                self.ns.metadata_identification,
                children,
                path,
                cardinality="array",
                datatype="ccmmmetadatarecord",
            ),
            "other_languages": self.languages_parser.parse_field(
                self.ns.other_language,
                children,
                path,
                cardinality="optional_array",
            ),
            "primary_language": self.languages_parser.parse_field(
                self.ns.primary_language,
                children,
                path,
                cardinality="optional",
            ),
            "provenances": self.parse_field(
                self.ns.provenance,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmprovenancestatement",
            ),
            "publication_year": self.parse_field(
                self.ns.publication_year,
                children,
                path,
                cardinality="single",
                datatype="int",
            ),
            "qualified_relations": self.parse_field(
                self.ns.qualified_relation,
                children,
                path,
                cardinality="array",
                datatype="ccmmresourcetoagentrelationship",
            ),
            "related_resources": self.parse_field(
                self.ns.related_resource,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmresource",
            ),
            "resource_type": self.resourcetypes_parser.parse_field(
                self.ns.resource_type,
                children,
                path,
                cardinality="optional",
            ),
            "subjects": self.parse_field(
                self.ns.subject,
                children,
                path,
                cardinality="array",
                datatype="ccmmsubject",
            ),
            "terms_of_use": self.parse_field(
                self.ns.terms_of_use,
                children,
                path,
                cardinality="single",
                datatype="ccmmtermsofuse",
            ),
            "time_references": self.parse_field(
                self.ns.time_reference,
                children,
                path,
                cardinality="array",
                datatype="ccmmtimereference",
            ),
            "title": self.parse_text_field(
                self.ns.title,
                children,
                path,
                cardinality="single",
            ),
            "validation_results": self.parse_field(
                self.ns.validation_result,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmvalidationresult",
            ),
            "version": self.parse_text_field(
                self.ns.version,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmdescription(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type description to CCMMDescription."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "description_text": self.parse_multilingual(
                self.ns.description_text,
                children,
                path,
                cardinality="single",
            ),
            "description_type": self.descriptiontypes_parser.parse_field(
                self.ns.description_type,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmdistribution(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type distribution to CCMMDistribution."""
        children = self.children(el)
        return {
            "distribution_data_service": self.parse_field(
                self.ns.distribution_data_service,
                children,
                path,
                cardinality="optional",
                datatype="ccmmdistributiondataservice",
            ),
            "distribution_downloadable_file": self.parse_field(
                self.ns.distribution_downloadable_file,
                children,
                path,
                cardinality="optional",
                datatype="ccmmdistributiondownloadablefile",
            ),
        }

    @datatype_parser()
    def parse_ccmmdistributiondataservice(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type distribution_data_service to CCMMDistributionDataService."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "access_services": self.parse_field(
                self.ns.access_service,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmdataservice",
            ),
            "description": self.parse_multilingual(
                self.ns.description,
                children,
                path,
                cardinality="optional",
            ),
            "documentations": self.parse_field(
                self.ns.documentation,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmdocumentation",
            ),
            "conforms_to_specifications": self.parse_field(
                self.ns.conforms_to_specification,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmapplicationprofile",
            ),
            "title": self.parse_text_field(
                self.ns.title,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmdistributiondownloadablefile(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type distribution_downloadable_file to CCMMDistributionDownloadableFile."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "access_urls": self.parse_field(
                self.ns.access_url,
                children,
                path,
                cardinality="array",
                datatype="ccmmfile",
            ),
            "byte_size": self.parse_field(
                self.ns.byte_size,
                children,
                path,
                cardinality="single",
                datatype="long",
            ),
            "checksum": self.parse_field(
                self.ns.checksum,
                children,
                path,
                cardinality="optional",
                datatype="ccmmchecksum",
            ),
            "conforms_to_schemas": self.parse_field(
                self.ns.conforms_to_schema,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmapplicationprofile",
            ),
            "download_urls": self.parse_field(
                self.ns.download_url,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmfile",
            ),
            "format": self.fileformats_parser.parse_field(
                self.ns.format,
                children,
                path,
                cardinality="single",
            ),
            "media_type": self.mediatypes_parser.parse_field(
                self.ns.media_type,
                children,
                path,
                cardinality="optional",
            ),
            "title": self.parse_text_field(
                self.ns.title,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmdocumentation(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type documentation to CCMMDocumentation."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="single",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmfile(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type file to CCMMFile."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="single",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmfundingreference(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type funding_reference to CCMMFundingReference."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "award_title": self.parse_text_field(
                self.ns.award_title,
                children,
                path,
                cardinality="optional",
            ),
            "funders": self.parse_field(
                self.ns.funder,
                children,
                path,
                cardinality="array",
                datatype="ccmmagent",
            ),
            "funding_program": self.parse_text_field(
                self.ns.funding_program,
                children,
                path,
                cardinality="optional",
            ),
            "local_identifier": self.parse_text_field(
                self.ns.local_identifier,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmidentifier(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type identifier to CCMMIdentifier."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "value": self.parse_text_field(
                self.ns.value,
                children,
                path,
                cardinality="single",
            ),
            "scheme": self.identifierschemes_parser.parse_field(
                self.ns.scheme,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmlicensedocument(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type license_document to CCMMLicenseDocument."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmlocation(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type location to CCMMLocation."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "bounding_boxes": self.parse_field(
                self.ns.bounding_box,
                children,
                path,
                cardinality="optional_array",
                datatype="gmlenvelopetype",
            ),
            "geometry": self.parse_field(
                self.ns.geometry,
                children,
                path,
                cardinality="optional",
                datatype="ccmmgeometry",
            ),
            "names": self.parse_text_field(
                self.ns.name,
                children,
                path,
                cardinality="optional_array",
            ),
            "related_objects": self.parse_field(
                self.ns.related_object,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmresource",
            ),
            "relation_type": self.locationrelationtypes_parser.parse_field(
                self.ns.relation_type,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmmetadatarecord(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type metadata_record to CCMMMetadataRecord."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "conforms_to_standards": self.parse_field(
                self.ns.conforms_to_standard,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmapplicationprofile",
            ),
            "date_created": self.parse_field(
                self.ns.date_created,
                children,
                path,
                cardinality="optional",
                datatype="date",
            ),
            "date_updated": self.parse_field(
                self.ns.date_updated,
                children,
                path,
                cardinality="optional",
                datatype="date",
            ),
            "languages": self.languages_parser.parse_field(
                self.ns.language,
                children,
                path,
                cardinality="optional_array",
            ),
            "original_repository": self.parse_field(
                self.ns.original_repository,
                children,
                path,
                cardinality="single",
                datatype="ccmmrepository",
            ),
            "qualified_relations": self.parse_field(
                self.ns.qualified_relation,
                children,
                path,
                cardinality="array",
                datatype="ccmmresourcetoagentrelationship",
            ),
        }

    @datatype_parser()
    def parse_ccmmorganization(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type organization to CCMMOrganization."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "alternate_names": self.parse_i18n(
                self.ns.alternate_name,
                children,
                path,
                cardinality="optional_array",
            ),
            "contact_points": self.parse_field(
                self.ns.contact_point,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmcontactdetails",
            ),
            "identifiers": self.parse_field(
                self.ns.identifier,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmidentifier",
            ),
            "name": self.parse_text_field(
                self.ns.name,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmperson(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type person to CCMMPerson."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "affiliations": self.parse_field(
                self.ns.affiliation,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmorganization",
            ),
            "contact_points": self.parse_field(
                self.ns.contact_point,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmcontactdetails",
            ),
            "family_names": self.parse_text_field(
                self.ns.family_name,
                children,
                path,
                cardinality="optional_array",
            ),
            "given_names": self.parse_text_field(
                self.ns.given_name,
                children,
                path,
                cardinality="optional_array",
            ),
            "identifiers": self.parse_field(
                self.ns.identifier,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmidentifier",
            ),
            "name": self.parse_text_field(
                self.ns.name,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmprovenancestatement(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type provenance_statement to CCMMProvenanceStatement."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmrepository(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type repository to CCMMRepository."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="single",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmresource(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type resource to CCMMResource."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "alternate_titles": self.parse_field(
                self.ns.alternate_title,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmalternatetitle",
            ),
            "identifiers": self.parse_field(
                self.ns.identifier,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmidentifier",
            ),
            "qualified_relations": self.parse_field(
                self.ns.qualified_relation,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmresourcetoagentrelationship",
            ),
            "resource_relation_type": self.resourcerelationtypes_parser.parse_field(
                self.ns.resource_relation_type,
                children,
                path,
                cardinality="optional",
            ),
            "resource_type": self.resourcetypes_parser.parse_field(
                self.ns.resource_type,
                children,
                path,
                cardinality="optional",
            ),
            "resource_url": self.parse_text_field(
                self.ns.resource_url,
                children,
                path,
                cardinality="optional",
            ),
            "time_references": self.parse_field(
                self.ns.time_reference,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmtimereference",
            ),
            "title": self.parse_text_field(
                self.ns.title,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmresourcetoagentrelationship(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type qualified_relation to CCMMResourceToAgentRelationship."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "relation": self.parse_field(
                self.ns.relation,
                children,
                path,
                cardinality="single",
                datatype="ccmmagent",
            ),
            "role": self.resourceagentroletypes_parser.parse_field(
                self.ns.role,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmsubject(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type subject to CCMMSubject."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "classification_code": self.parse_text_field(
                self.ns.classification_code,
                children,
                path,
                cardinality="optional",
            ),
            "definition": self.parse_multilingual(
                self.ns.definition,
                children,
                path,
                cardinality="optional",
            ),
            "subject_scheme": self.subjectschemes_parser.parse_field(
                self.ns.subject_scheme,
                children,
                path,
                cardinality="optional",
            ),
            "title": self.parse_multilingual(
                self.ns.title,
                children,
                path,
                cardinality="single",
            ),
        }

    @datatype_parser()
    def parse_ccmmtermsofuse(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type terms_of_use to CCMMTermsOfUse."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "access_rights": self.accessrights_parser.parse_field(
                self.ns.access_rights,
                children,
                path,
                cardinality="single",
            ),
            "contact_points": self.parse_field(
                self.ns.contact_point,
                children,
                path,
                cardinality="optional_array",
                datatype="ccmmagent",
            ),
            "description": self.parse_multilingual(
                self.ns.description,
                children,
                path,
                cardinality="optional",
            ),
            "license": self.parse_field(
                self.ns.license,
                children,
                path,
                cardinality="single",
                datatype="ccmmlicensedocument",
            ),
        }

    @datatype_parser()
    def parse_ccmmtimeinstant(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type time_instant to CCMMTimeInstant."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "date_time": self.parse_field(
                self.ns.date_time,
                children,
                path,
                cardinality="optional",
                datatype="datetime",
            ),
            "date": self.parse_field(
                self.ns.date,
                children,
                path,
                cardinality="optional",
                datatype="date",
            ),
        }

    @datatype_parser()
    def parse_ccmmtimeinterval(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type time_interval to CCMMTimeInterval."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "beginning": self.parse_field(
                self.ns.beginning,
                children,
                path,
                cardinality="single",
                datatype="ccmmtimeinstant",
            ),
            "end": self.parse_field(
                self.ns.end,
                children,
                path,
                cardinality="single",
                datatype="ccmmtimeinstant",
            ),
        }

    @datatype_parser()
    def parse_ccmmtimereference(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type time_reference to CCMMTimeReference."""
        children = self.children(el)
        return {
            "temporal_representation": self.parse_field(
                self.ns.temporal_representation,
                children,
                path,
                cardinality="single",
                datatype="ccmmtimerepresentation",
            ),
            "date_type": self.datetypes_parser.parse_field(
                self.ns.date_type,
                children,
                path,
                cardinality="optional",
            ),
            "date_information": self.parse_i18n(
                self.ns.date_information,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmtimerepresentation(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type CCMMTimeRepresentation to CCMMTimeRepresentation."""
        children = self.children(el)
        return {
            "time_interval": self.parse_field(
                self.ns.time_interval,
                children,
                path,
                cardinality="optional",
                datatype="ccmmtimeinterval",
            ),
            "time_instant": self.parse_field(
                self.ns.time_instant,
                children,
                path,
                cardinality="optional",
                datatype="ccmmtimeinstant",
            ),
        }

    @datatype_parser()
    def parse_ccmmvalidationresult(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type validation_result to CCMMValidationResult."""
        children = self.children(el)
        return {
            "iri": self.parse_text_field(
                self.ns.iri,
                children,
                path,
                cardinality="optional",
            ),
            "label": self.parse_multilingual(
                self.ns.label,
                children,
                path,
                cardinality="optional",
            ),
        }

    @datatype_parser()
    def parse_ccmmwkt(self, el: Element, path: list[QualifiedTag]) -> dict:
        """Parse an element of type wkt to CCMMWKT."""
        children = self.children(el)
        return {
            "value": self.parse_text_field(
                self.ns.value,
                children,
                path,
                cardinality="optional",
            ),
            "srs_name": self.parse_text_field(
                self.ns.srs_name,
                children,
                path,
                cardinality="optional",
            ),
        }

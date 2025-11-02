# Schema Overview

## Type: access_rights

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: address

| Name | Type | Required | Array |
|------|------|----------|-------|
| address_area | string |  | ✔️ |
| administrative_unit_level_1 | string |  | ✔️ |
| administrative_unit_level_2 | string |  | ✔️ |
| full_address | string |  | ✔️ |
| iri | anyURI |  |  |
| label | multilingual |  |  |
| locator_designator | string |  | ✔️ |
| locator_name | string |  | ✔️ |
| po_box | string |  | ✔️ |
| post_code | string |  | ✔️ |
| post_name | string |  | ✔️ |
| thoroughfare | string |  | ✔️ |

## Type: agent

| Name | Type | Required | Array |
|------|------|----------|-------|
| organization | organization | ✔️ |  |
| person | anonymous | ✔️ |  |

## Type: alternate_title

| Name | Type | Required | Array |
|------|------|----------|-------|
| alternate_title_type | alternate_title_type |  |  |
| iri | anyURI |  |  |
| title | multilingual | ✔️ |  |

## Type: alternate_title_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: application_profile

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: checksum

| Name | Type | Required | Array |
|------|------|----------|-------|
| algorithm | anyURI | ✔️ |  |
| checksum_value | hexBinary | ✔️ |  |
| iri | anyURI |  |  |

## Type: checksum_algorithm

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |

## Type: contact_details

| Name | Type | Required | Array |
|------|------|----------|-------|
| address | address |  | ✔️ |
| dataBox | string |  | ✔️ |
| email | string |  | ✔️ |
| iri | anyURI |  |  |
| phone | string |  | ✔️ |

## Type: data_service

| Name | Type | Required | Array |
|------|------|----------|-------|
| endpoint_url | resource | ✔️ | ✔️ |
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: dataset

| Name | Type | Required | Array |
|------|------|----------|-------|
| alternate_title | alternate_title |  | ✔️ |
| description | description |  | ✔️ |
| distribution | distribution |  | ✔️ |
| funding_reference | funding_reference |  | ✔️ |
| identifier | identifier | ✔️ | ✔️ |
| iri | anyURI |  |  |
| location | location |  | ✔️ |
| metadata_identification | metadata_record | ✔️ | ✔️ |
| other_language | language_system |  | ✔️ |
| primary_language | language_system |  |  |
| provenance | provenance_statement |  | ✔️ |
| publication_year | gYear | ✔️ |  |
| qualified_relation | resource_to_agent_relationship | ✔️ | ✔️ |
| related_resource | resource |  | ✔️ |
| resource_type | resource_type |  |  |
| subject | subject | ✔️ | ✔️ |
| terms_of_use | terms_of_use | ✔️ |  |
| time_reference | type | ✔️ | ✔️ |
| title | string | ✔️ |  |
| validation_result | validation_result |  | ✔️ |
| version | string |  |  |

## Type: date_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: description

| Name | Type | Required | Array |
|------|------|----------|-------|
| description_text | multilingual | ✔️ |  |
| description_type | description_type |  |  |
| iri | anyURI |  |  |

## Type: description_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI |  |  |
| label | multilingual |  |  |

## Type: distribution

| Name | Type | Required | Array |
|------|------|----------|-------|
| distribution_data_service | anonymous | ✔️ |  |
| distribution_downloadable_file | anonymous | ✔️ |  |

## Type: documentation

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: file

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: format

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: funding_reference

| Name | Type | Required | Array |
|------|------|----------|-------|
| award_title | string |  |  |
| funder | agent | ✔️ | ✔️ |
| funding_program | anyURI |  |  |
| iri | anyURI |  |  |
| local_identifier | string |  |  |

## Type: geometry

| Name | Type | Required | Array |
|------|------|----------|-------|
|  | anonymous |  |  |
| iri | anyURI |  |  |
| label | multilingual |  |  |
| wkt | anonymous |  |  |

## Type: identifier

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI |  |  |
| scheme | identifier_scheme | ✔️ |  |
| value | string | ✔️ |  |

## Type: identifier_scheme

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: language_system

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: license_document

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI |  |  |
| label | multilingual |  |  |

## Type: location

| Name | Type | Required | Array |
|------|------|----------|-------|
| bounding_box | EnvelopeType |  | ✔️ |
| geometry | geometry |  |  |
| iri | anyURI |  |  |
| name | string |  | ✔️ |
| related_object | resource |  | ✔️ |
| relation_type | relation_type | ✔️ |  |

## Type: media_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: metadata_record

| Name | Type | Required | Array |
|------|------|----------|-------|
| conforms_to_standard | application_profile |  | ✔️ |
| date_created | date |  |  |
| date_updated | date |  | ✔️ |
| iri | anyURI |  |  |
| language | language_system |  | ✔️ |
| original_repository | repository | ✔️ |  |
| qualified_relation | resource_to_agent_relationship | ✔️ | ✔️ |

## Type: organization

| Name | Type | Required | Array |
|------|------|----------|-------|
| alternate_name | multilingual |  |  |
| contact_point | contact_details |  | ✔️ |
| identifier | identifier |  | ✔️ |
| iri | anyURI |  |  |
| name | string | ✔️ |  |

## Type: provenance_statement

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI |  |  |
| label | multilingual |  |  |

## Type: relation_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: repository

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: resource

| Name | Type | Required | Array |
|------|------|----------|-------|
| alternate_title | alternate_title |  | ✔️ |
| identifier | identifier |  | ✔️ |
| iri | anyURI |  |  |
| qualified_relation | resource_to_agent_relationship |  | ✔️ |
| resource_relation_type | resource_relation_type |  |  |
| resource_type | resource_type |  |  |
| resource_url | anyURI |  |  |
| time_reference | time_reference |  | ✔️ |
| title | string |  |  |

## Type: resource_agent_role_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: resource_relation_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: resource_to_agent_relationship

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI |  |  |
| relation | agent | ✔️ |  |
| role | resource_agent_role_type | ✔️ |  |

## Type: resource_type

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: subject

| Name | Type | Required | Array |
|------|------|----------|-------|
| classification_code | string |  |  |
| definition | multilingual |  |  |
| iri | anyURI |  |  |
| subject_scheme | subject_scheme |  |  |
| title | multilingual | ✔️ |  |

## Type: subject_scheme

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI | ✔️ |  |
| label | multilingual |  |  |

## Type: terms_of_use

| Name | Type | Required | Array |
|------|------|----------|-------|
| access_rights | access_rights | ✔️ |  |
| contact_point | agent |  | ✔️ |
| description | multilingual |  |  |
| iri | anyURI |  |  |
| license | license_document | ✔️ |  |

## Type: time_instant

| Name | Type | Required | Array |
|------|------|----------|-------|
| date_information | multilingual |  |  |
| iri | anyURI |  |  |

## Type: time_interval

| Name | Type | Required | Array |
|------|------|----------|-------|
| beginning | time_instant | ✔️ |  |
| date_information | multilingual |  |  |
| date_type | date_type | ✔️ |  |
| end | time_instant | ✔️ |  |
| iri | anyURI |  |  |

## Type: type

| Name | Type | Required | Array |
|------|------|----------|-------|
| time_instant | time_instant | ✔️ |  |
| time_interval | time_interval | ✔️ |  |

## Type: validation_result

| Name | Type | Required | Array |
|------|------|----------|-------|
| iri | anyURI |  |  |
| label | multilingual |  |  |


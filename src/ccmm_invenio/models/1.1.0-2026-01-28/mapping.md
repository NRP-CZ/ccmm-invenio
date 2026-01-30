| CCMM XSD | NMA CCMM YAML | Production CCMM YAML |
|----------------|----------------|---------------------|
| address/schema.xsd | CCMMAddress | |
| agent/schema.xsd | CCMMAgent | |
| alternate-title/schema.xsd | CCMMAlternateTitle | |
| checksum/schema.xsd | CCMMChecksum | |
| contact-details/schema.xsd | CCMMContactDetails | |
| data-service/schema.xsd | CCMMDataService | |
| dataset/schema.xsd | CCMMDataSet | |
| description/schema.xsd | CCMMDescription | |
| distribution/schema.xsd | CCMMDistribution | |
| distribution/schema.xsd | CCMMDistributionDataService | |
| distribution/schema.xsd | CCMMDistributionDownloadableFile | |
| documentation/schema.xsd | CCMMDocumentation | |
| file/schema.xsd | CCMMFile | |
| funding-reference/schema.xsd | CCMMFundingReference | |
| geometry/schema.xsd | CCMMGeometry | |
| identifier/schema.xsd | CCMMIdentifier | |
| license-document/schema.xsd | CCMMLicenseDocument | |
| location/schema.xsd | CCMMLocation | |
| metadata-record/schema.xsd | CCMMMetadataRecord | |
| organization/schema.xsd | CCMMOrganization | |
| agent/schema.xsd | CCMMPerson | |
| provenance-statement/schema.xsd | CCMMProvenanceStatement | |
| repository/schema.xsd | CCMMRepository | |
| resource/schema.xsd | CCMMResource | |
| resource-to-agent-relationship/schema.xsd | CCMMResourceToAgentRelationship | |
| subject/schema.xsd | CCMMSubject | |
| terms-of-use/schema.xsd | CCMMTermsOfUse | |
| time-instant/schema.xsd | CCMMTimeInstant | |
| time-interval/schema.xsd | CCMMTimeInterval | |
| time-reference/schema.xsd | CCMMTimeReference | |
| validation-result/schema.xsd | CCMMValidationResult | |
| geometry/schema.xsd | CCMMWKT | |

## Inconsistencies

### alternate-title/schema.xsd | CCMMAlternateTitle 

*title:* XSD defines multilingual array (maxOccurs="unbounded" with xml:lang) but CCMM defines as single title field without multilingual type

### checksum/schema.xsd | CCMMChecksum 

*checksum_value:* XSD defines as hexBinary type but CCMM does not specify type constraint
*algorithm:* XSD defines as anyURI type but CCMM does not specify type constraint

### contact-details/schema.xsd | CCMMContactDetails 

*Field names:* XSD uses singular names (address, dataBox, email, phone) but CCMM uses pluralized names (addresses, dataBoxes, emails, phones)  
*Consistent with CCMM pluralization rule for arrays*

### data-service/schema.xsd | CCMMDataService 

*endpoint_url vs endpoint_urls:* XSD uses singular name but CCMM uses pluralized name (consistent with CCMM array rule)
*label:* XSD defines multilingual array but CCMM does not specify multilingual type
*iri:* XSD defines as required but CCMM defines as optional

### dataset/schema.xsd | CCMMDataSet 

*title:* XSD defines as simple string but CCMM should use multilingual type for consistency
*time_reference:* XSD defines as type 'type' (seems incorrect) but CCMM uses time_references array with proper type
*metadata_identification vs metadata_identifications:* XSD uses singular but CCMM pluralized (correct per rules)

### description/schema.xsd | CCMMDescription 

*description_text:* XSD defines multilingual field with xml:lang but CCMM does not specify multilingual type

### distribution/schema.xsd | CCMMDistribution 

*Structure:* XSD uses choice between distribution_data_service and distribution_downloadable_file but CCMM has separate types

### distribution/schema.xsd | CCMMDistributionDataService 

*description:* XSD defines multilingual field but CCMM uses type: multilingual correctly
*title:* XSD defines multilingual field but CCMM does not specify type correctly
*specification vs specifications:* XSD uses singular but CCMM pluralized (correct per rules)
*access_service vs access_services:* XSD uses singular but CCMM pluralized (correct per rules)

### distribution/schema.xsd | CCMMDistributionDownloadableFile 

*title:* XSD defines multilingual field but CCMM does not specify type correctly  
*access_url vs access_urls:* XSD uses singular but CCMM pluralized (correct per rules)
*download_url vs download_urls:* XSD uses singular but CCMM pluralized (correct per rules)
*conforms_to_schema vs conforms_to_schemas:* XSD uses singular but CCMM pluralized (correct per rules)

### documentation/schema.xsd | CCMMDocumentation 

*label:* XSD defines multilingual array but CCMM does not specify multilingual type

### file/schema.xsd | CCMMFile 

*label:* XSD defines multilingual array but CCMM does not specify multilingual type

### funding-reference/schema.xsd | CCMMFundingReference 

*funder vs funders:* XSD uses singular but CCMM pluralized (correct per rules)

### geometry/schema.xsd | CCMMGeometry 

*label:* XSD defines multilingual array but CCMM does not specify multilingual type
*wkt structure:* XSD defines complex type with srsName attribute but CCMM CCMMWKT only has value field

### identifier/schema.xsd | CCMMIdentifier 

No major inconsistencies detected

### license-document/schema.xsd | CCMMLicenseDocument 

*label:* XSD defines multilingual array but CCMM does not specify multilingual type

### location/schema.xsd | CCMMLocation 

*bounding_box vs bounding_boxes:* XSD uses singular but CCMM pluralized (correct per rules)
*name vs names:* XSD uses singular but CCMM pluralized (correct per rules)  
*related_object vs related_objects:* XSD uses singular but CCMM pluralized (correct per rules)

### metadata-record/schema.xsd | CCMMMetadataRecord 

*conforms_to_standard vs conforms_to_standards:* XSD uses singular but CCMM pluralized (correct per rules)
*date_updated vs dates_updated:* XSD uses singular but CCMM pluralized (correct per rules)
*language vs languages:* XSD uses singular but CCMM pluralized (correct per rules)
*qualified_relation:* XSD requires multiple (minOccurs="2") but CCMM shows as array type

### organization/schema.xsd | CCMMOrganization 

*alternate_name vs alternate_names:* XSD uses singular but CCMM pluralized (correct per rules)
*contact_point vs contact_points:* XSD uses singular but CCMM pluralized (correct per rules)
*alternate_name:* XSD defines multilingual array but CCMM does not specify multilingual type

### agent/schema.xsd | CCMMPerson 

*given_name vs given_names:* XSD uses singular but CCMM pluralized (correct per rules)
*family_name vs family_names:* XSD uses singular but CCMM pluralized (correct per rules)
*Missing fields:* CCMM Person missing affiliation, contact_point, identifier, iri from XSD

### provenance-statement/schema.xsd | CCMMProvenanceStatement 

*label:* XSD defines multilingual array but CCMM does not define any properties beyond iri

### repository/schema.xsd | CCMMRepository 

*label:* XSD defines multilingual array but CCMM does not define any properties beyond iri
*iri:* XSD defines as required but CCMM defines as optional

### resource/schema.xsd | CCMMResource 

*alternate_title vs alternate_titles:* XSD uses singular but CCMM should use pluralized name
*time_reference vs time_references:* XSD uses singular but CCMM should use pluralized name
*qualified_relation vs qualified_relations:* XSD uses singular but CCMM should use pluralized name
*CCMM missing fields:* CCMM Resource does not define any of the XSD fields

### resource-to-agent-relationship/schema.xsd | CCMMResourceToAgentRelationship 

*CCMM missing fields:* CCMM ResourceToAgentRelationship does not define any properties (only has iri)

### subject/schema.xsd | CCMMSubject 

*title:* XSD defines multilingual array but CCMM does not specify multilingual type  
*definition vs definitions:* XSD uses singular but CCMM should use pluralized name
*definition:* XSD defines multilingual array but CCMM should use multilingual type
*CCMM missing fields:* CCMM Subject does not define XSD properties like classification_code, definitions, subject_scheme, title

### terms-of-use/schema.xsd | CCMMTermsOfUse 

*contact_point vs contact_points:* XSD uses singular but CCMM should use pluralized name  
*description vs descriptions:* XSD uses singular but CCMM should use pluralized name
*description:* XSD defines multilingual array but CCMM should use multilingual type
*CCMM missing fields:* CCMM TermsOfUse does not define any properties beyond iri

### time-instant/schema.xsd | CCMMTimeInstant 

*date/datetime vs edtf:* XSD uses choice between date and dateTime but CCMM uses EDTF format (as noted in YAML comments)
*date_information:* XSD defines multilingual field but CCMM does not define this field

### time-interval/schema.xsd | CCMMTimeInterval 

*Structure mismatch:* XSD defines beginning/end as time_instant but CCMM does not define proper structure
*date_information:* XSD defines multilingual field but CCMM does not define this field
*Missing fields:* CCMM TimeInterval does not define XSD properties

### time-reference/schema.xsd | CCMMTimeReference 

*Structure:* XSD uses choice between time_instant and time_interval but CCMM only defines time_interval property
*Different structure:* XSD time_reference is incorrectly named 'type' and has different internal structure than standalone time_instant/time_interval

### validation-result/schema.xsd | CCMMValidationResult 

*label:* XSD defines multilingual array but CCMM does not define any properties beyond iri

### geometry/schema.xsd | CCMMWKT 

*srsName attribute:* XSD WKT has optional srsName attribute but CCMM CCMMWKT only has value field


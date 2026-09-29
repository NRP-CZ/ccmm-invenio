The CCMM types of `ccmm.yaml` used by the model (the parts of CCMM stored in their CCMM shape - distributions,
agents, identifiers, time references, application profiles, repositories, ...). The dataset itself
is `CCMMDataset` in `ccmm-invenio.yaml` (RDM based), with its own `CCMMInvenioRelatedResource` and
`CCMMInvenioMetadataRecord`; the CCMM types used only by the former NMA model were removed.

| CCMM XSD | CCMM YAML |
|----------------|----------------|
| address/schema.xsd | CCMMAddress |
| agent/schema.xsd | CCMMAgent |
| alternate-title/schema.xsd | CCMMAlternateTitle |
| checksum/schema.xsd | CCMMChecksum |
| contact-details/schema.xsd | CCMMContactDetails |
| data-service/schema.xsd | CCMMDataService |
| distribution/schema.xsd | CCMMDistribution |
| distribution/schema.xsd | CCMMDistributionDataService |
| distribution/schema.xsd | CCMMDistributionDownloadableFile |
| documentation/schema.xsd | CCMMDocumentation |
| file/schema.xsd | CCMMFile |
| identifier/schema.xsd | CCMMIdentifier |
| organization/schema.xsd | CCMMOrganization |
| agent/schema.xsd | CCMMPerson |
| repository/schema.xsd | CCMMRepository |
| resource/schema.xsd | CCMMResource |
| resource-to-agent-relationship/schema.xsd | CCMMResourceToAgentRelationship |
| time-instant/schema.xsd | CCMMTimeInstant |
| time-interval/schema.xsd | CCMMTimeInterval |
| time-reference/schema.xsd | CCMMTimeReference |

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

### identifier/schema.xsd | CCMMIdentifier 

No major inconsistencies detected

### organization/schema.xsd | CCMMOrganization 

*alternate_name vs alternate_names:* XSD uses singular but CCMM pluralized (correct per rules)
*contact_point vs contact_points:* XSD uses singular but CCMM pluralized (correct per rules)
*alternate_name:* XSD defines multilingual array but CCMM does not specify multilingual type

### agent/schema.xsd | CCMMPerson 

*given_name vs given_names:* XSD uses singular but CCMM pluralized (correct per rules)
*family_name vs family_names:* XSD uses singular but CCMM pluralized (correct per rules)
*Missing fields:* CCMM Person missing affiliation, contact_point, identifier, iri from XSD

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

# CCMM support in Invenio(RDM)

## Rationale

The CCMM model inside invenio is constructed in a sense that it is as close to InvenioRDM maintrunk as possible. This could mean that some features of CCMM are not available out of the box and would need to be implemented by repository creators in case they are needed.

This document summarizes the differences between the CCMM model in Invenio and the CCMM 1.1.0 model defined as a xml schema on the  [https://www.ccmm.cz/](https://www.ccmm.cz/) website.

## Import from CCMM xml into Invenio

Not all features of CCMM are supported in Invenio and are not converted during the import. This does not mean they will not be present in the metadata record. They are, inside the `ccmm_xml` field, which contains the raw CCMM xml as it was imported.

**How vocabulary items are matched on import.** A CCMM vocabulary item (an `{iri, label}` pair) is
matched to an item of the repository's vocabularies by its iri - an exact match first, then a
narrower (more specific) mapping. The match is strict: a document referencing an unknown vocabulary
iri is **rejected** on import. The label the document carries is ignored; labels are always taken
from the vocabulary, so the repository's own wording and translations apply. Codelists whose iris
end in the item's code (file types, media types, checksum algorithms) are also matched by that code,
case-insensitively (`…/file-type/TAR` → `tar`). A few exceptions are lenient by design: an unmatched
subject becomes a keyword, funders and affiliations are matched by their ROR against the
repository's records (a miss just keeps the name, without the identifier), an unknown identifier
scheme is guessed from the identifier itself (a `https://doi.org/…` iri becomes a doi, otherwise
`url` or `other`), and an unknown license becomes a free-text license.

The following table summarizes what does not survive the import unchanged (schema code:
`src/ccmm_invenio/resources/serializers/ccmm/schema/`, one row per CCMM area):

| CCMM element | Import behaviour | Detail |
|---|---|---|
| `validation_result`, `provenance`, foreign-namespace extensions (`xs:any`) | **not converted** | no Invenio counterpart (`DatasetMetadataSchema.Meta`) |
| `iri` of titles/descriptions/dates/agents/locations/terms_of_use… (most elements carry an optional `iri`) | **not converted** | kept only where it is a first-class Invenio field (dataset `iri`, related-resource `iri`, location/subject IRIs) |
| `contact_point` (of persons/organizations in `qualified_relation`, of the metadata record's agents, of `terms_of_use`) | **not converted** | no Invenio counterpart |
| `identifier/authorized` | **not converted** | no Invenio counterpart |
| organization `alternate_name` | **not converted** | no Invenio counterpart |
| vocabulary item `{iri, label}` | **modified** | becomes the Invenio `{id}` found in the SKOS mappings (`exactMatch`/`narrowMatch`); an unknown IRI is a **validation error**; with `id_prefix`, an IRI in the vocabulary namespace is also looked up by the lower-cased rest (`…/file-type/TAR` → `tar`) |
| `qualified_relation` | **split by role** | Creator → `creators`, Publisher → `publisher`, any other role → `contributors` |
| Publisher agent(s) | **modified** | RDM publisher is a string: names joined by `", "`; a person publisher becomes a name only (ORCID/given/family lost); exported back as one organization |
| Creator role | **modified** | role label/IRI not converted (creators are the Creator role by definition) |
| person `given_name`, `family_name` (0..n each) | **modified** | joined with a space into a single RDM name |
| `terms_of_use/access_rights` | **moved** | becomes the record `access` (not metadata): open / metadata-only → `files.enabled=false` / embargoed (end = the "Available" date) / restricted |
| `terms_of_use/license` | **modified** | vocabulary license → `rights.{id}`; unknown license → free-text `{title, link: iri}`; the `description` is not converted when the license is a vocabulary one (RDM does not accept both) |
| unknown/local identifier `scheme` | **modified** | falls back to scheme detection from the `iri` (a DOI becomes a `doi`), otherwise `url` with the IRI as the value, otherwise `other` |
| identifier `authorized`, and `iri` | **not converted / derived** | `iri` on load only for the scheme fallback; on export derived from identifier+scheme |
| multilingual text in fields having a single RDM locale (title/description/license title) | **modified** | the variant in the default locale is used (else the first configured-locale variant, else the first); other variants not converted |
| `xml:lang=""` | **renamed** | becomes language `und` (and is added to `languages_primary`) |
| `date_information` (time reference description) | **modified** | becomes plain text; its language is not converted |
| `date_time`/tz on dates, time-of-day in intervals, `xs:date` timezones | **trimmed** | RDM EDTF has dates and level-0 intervals only (e.g. `2025`) |
| `primary_language` | **merged** | goes first into `languages` together with `other_language`; which one was primary is not stored |
| `subject` | **modified** | IRI in the subjects vocabulary → `{id}`; otherwise one keyword per language variant of the title (RDM keywords have no language); `definition`, `classification_code`, `subject_scheme` not stored (re-derived from the vocabulary on export) |
| funder / affiliation identifiers | **modified** | only a ROR present in the funders/affiliations vocabulary becomes the `id`; other identifiers not converted; a person funder becomes a name (RDM funders are organizations) |
| `location` | **modified** | GML/WKT reprojected to WGS84 GeoJSON; a multi-polygon is **split** into polygons; geometry label, `bounding_box` (when a geometry exists), original CRS and `related_object.title` not converted; names joined with `; "`; only the configured RDM location identifier schemes kept |
| downloadable-file `distribution` with access/download URL on this server | **not converted** | its metadata would duplicate the uploaded file entry (see `DistributionsField`) |
| `resource_type` missing | **defaulted** | `dataset` (RDM requires it) |
| `publication_year` | **modified** | becomes `publication_date`: the "Created" time reference wins, otherwise `<year>-01-01` |
| `metadata_identification` | **kept (CCMM-shaped)** | stored and exported unchanged, but the record's agents share the contributor schema - their `contact_point`, `alternate_name`, agent `iri` are not converted |
| record `related_identifiers` | **derived** | regenerated from `related_resources` on create/update (a client-sent value is overwritten; not in the `application/json` API) |
| related resource without `title` | **defaulted** | the `iri` / `resource_url` becomes the title (required in the model) |

## Export from Invenio into CCMM xml

The export regenerates the xml from the record (the stored `ccmm_xml` is **not** replayed, the record may
have been edited since the import). It is best effort: an XSD problem is logged as a warning, not an
error, so a record created natively in Invenio may export an incomplete CCMM document.

**How vocabulary items are exported.** Every `{id}` reference is read from the vocabulary and written
back as `{iri, label}`: the iri from the item's SKOS `exactMatch` (or `broadMatch`) mapping,
otherwise the URL of the vocabulary detail page; the labels are the item's multilingual titles, so
wording and order follow our vocabularies, not the imported xml. The same rule covers the access
status → COAR access-rights iri and the subject scheme name. The Creator / Publisher roles are
synthetic (RDM has no role for them) - their label is resolved by the same `exactMatch` lookup in
the roles vocabularies, a bare iri when the fixtures are not loaded.

| Invenio (RDM) | Export behaviour | Detail |
|---|---|---|
| uploaded files | **added** | become downloadable-file distributions - only those the reader may see (REST: `read_files`; OAI-PMH: public record with public files; hidden files never) |
| `metadata_identifications` stored on the record | **as-is** | harvested metadata records are exported unchanged |
| no stored `metadata_identifications` | **generated** | one is made from `created`/`updated`/`links.self`; Data Manager = contributors with the `datamanager` role (they stay contributors), otherwise the repository (`THEME_SITENAME`); `conforms_to_standard` = CCMM RD 1.1.0, `original_repository` = this repository; `language` not known, not exported |
| record `access` | **converted** | `access.status` (or the embargo/files state) → `terms_of_use/access_rights` (open / metadata-only / embargoed / restricted) |
| `metadata.related_identifiers` | **not exported** | RDM-only, derived from `related_resources` for DataCite/search; CCMM carries `related_resource` instead |
| RDM main `description` | **reshaped** | exported as the first `description` element, of type "other" (it has no CCMM counterpart of its own); the `additional_descriptions` follow |
| every vocabulary reference `{id}` | **enriched** | exported as `{iri, label}` - the IRI from the SKOS `exactMatch` (or `broadMatch`) mapping, otherwise the vocabulary detail-page URL; labels from our vocabularies, so wording/order may differ from the source xml |
| `publisher` (RDM string) | **reshaped** | exported as one organization; a person publisher is only the name (ORCID etc. was already lost on import) |
| creators' role | **added** | exported with the Creator role IRI and its vocabulary label; same for the Publisher role (a bare IRI when the roles vocabulary is not loaded) |
| RDM `rights` list (0..n) | **first item only** | CCMM `terms_of_use` is 1..1 - further items are not exported; `description` exported only for a free-text license |
| organization affiliation of an organization | **not exported** | CCMM affiliations exist on persons only |
| `publication_date` | **reshaped** | only the year is exported as `publication_year`; a "Created" date is additionally a time reference |
| RDM dates | **reshaped** | EDTF reduced precision (`2025`, `2025-04`) exports as an interval spanning the year/month (CCMM has full dates only); date descriptions export with `xml:lang=""` (RDM descriptions have no language) |
| `languages` | **reshaped** | the first language becomes `primary_language`, the rest `other_language` |
| subjects `{id}` | **enriched** | IRI + titles from the vocabulary; `classification_code` (vocabulary prop, or the id without the scheme prefix) and the scheme (English name only); keyword subjects export with `xml:lang=""` and no language |
| funders / affiliations | **enriched** | the ROR `id` exports as the organization identifier; other identifiers do not exist in RDM |
| `locations` (GeoJSON, WGS84) | **reshaped** | each feature → one CCMM location; geometry as WKT in WGS84 (whitespace normalised, multi-polygons stay split); identifiers → `related_object`; place names split back on `; "`; the relation type is matched by its title, fallback `other`; original GML/CRS and `bounding_box` are not restored |
| person names | **rebuilt** | RDM display name ("Family, Given"), `given_name`/`family_name` exported as single-item lists |
| multilingual `und` language | **renamed** | exported as `xml:lang=""` |
| downloadable file `format` / `checksum` / `media_type` | **derived** | from extension/media type (unknown → `bin`), from the `md5:...` checksum prefix, the media type only when it is in the vocabulary |
| `ccmm_xml` field | **not exported** | keeps the source xml of the import on the record; the exported xml is always regenerated |

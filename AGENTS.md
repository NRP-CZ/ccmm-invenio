# AGENTS.md

Guide for people and coding agents working on `ccmm-invenio`: what the library is for, where
things live, the decisions behind the CCMM ↔ Invenio conversion, and how to work on it safely.
Read this before changing the models, the conversion schemas or the vocabulary fixtures.

## Purpose and direction

`ccmm-invenio` makes the **CCMM** (Czech Core Metadata Model, research data, currently
`1.1.0-2026-01-29`) usable in NRP Invenio (InvenioRDM + OARepo):

* an OARepo **model preset** for datasets (`ccmm_preset_1_1_0`),
* **CCMM XML import and export** (REST, OAI-PMH),
* **vocabulary fixtures** (converted from CCMM, COAR, DataCite, EU, IANA, INSPIRE, … sources),
* UI components (deposit form, detail page).

Intentions guiding the current work:

* **One model.** `ccmm_preset_1_1_0` (alias `ccmm_production_preset_1_1_0`) is the only model:
  RDM field types wherever RDM has an equivalent, CCMM-shaped types for the rest. The former NMA
  model (CCMM shape 1:1, for the national metadata aggregator) was removed together with the
  CCMM types only it used. Repositories may also contain parts where **3rd party records are
  harvested**, so the model must carry what a harvested record needs (e.g. its
  `metadata_identification`, see below).
* **Round trip as complete as possible without changing the RDM-based metadata schema.**
  CCMM XML → record → CCMM XML should lose as little as possible. Known remaining losses are
  listed in [Known gaps](#known-gaps-and-open-items).
* **Reuse RDM.** RDM features (DataCite DOI registration, search, the landing page, access,
  files) must keep working; CCMM-only data is added next to RDM data, not instead of it.

## Repository layout

| Path | What |
|---|---|
| `src/ccmm_invenio/models/__init__.py` | the preset (`ccmm_preset_1_1_0`, alias `ccmm_production_preset_1_1_0`); the oarepo-model customization classes live in `models/customizations.py` |
| `src/ccmm_invenio/models/1.1.0-2026-01-29/` | model yaml: `ccmm.yaml` (the CCMM types the model stores in their CCMM shape - distributions, agents, identifiers, …; `mapping.md` lists their XSD differences), `ccmm-invenio.yaml` (the dataset `CCMMDataset` and its own types), `ccmm-vocabularies.yaml` (CCMM vocabulary types → invenio vocabulary types). Keep them free of unused types |
| `src/ccmm_invenio/resources/serializers/ccmm/converter.py` | XML ↔ generic JSON (`convert_xml_to_json`, `convert_json_to_xml`, `XMLToGenericJSONConverter`, xmlschema based, validated against `xsd/ccmm-1.1.0-2026-01-29.xsd` in the same package) |
| `src/ccmm_invenio/resources/serializers/ccmm/schema/` | marshmallow schemas generic JSON ↔ invenio record (see below) |
| `src/ccmm_invenio/resources/deserializers/ccmm.py` | `CCMMJSONDeserializer` (the import deserializer) |
| `src/ccmm_invenio/resources/serializers/ccmm/__init__.py` | `CCMMXMLSerializer` (REST + OAI-PMH export) |
| `src/ccmm_invenio/resources/serializers/json.py` | the `application/json` serializer (without `metadata.related_identifiers` - those are derived, see `services/components/related_identifiers.py`) |
| `src/ccmm_invenio/resources/serializers/ui/` | UI serialization schemas (related resources) |
| `src/ccmm_invenio/services/components/` | record service components: `related_identifiers.py` (deriving RDM `related_identifiers` from `related_resources`), `root_record.py` (keeping `ccmm_xml` on the record) |
| `src/ccmm_invenio/fixtures/compiler/` | the vocabulary fixture compiler (readers, mergers, SSSOM mappings, invenio export) - build-time tool, optional `compile-vocabularies` deps |
| `src/ccmm_invenio/fixtures/input/vocabularies/` | hand-curated vocabulary inputs of the compiler (overlays, fragments, SSSOM) |
| `src/ccmm_invenio/fixtures/` | **generated** vocabulary fixtures: the `vocabularies.yaml` index at the package root (where the RDM extension fixture loader expects it via the `invenio_rdm_records.fixtures` entry point), `data/` with the `*.yaml` data files and `*.ttl` graphs |
| `ccmm_versions/ccmm-xml-releases/<version>/` | CCMM XSDs and the **metadata samples** (`metadata-samples/xml/*.xml`) used by the tests |
| `tests/` | pytest suite (`tests/model.py` registers the test model, `tests/vocabularies/` tests the fixture compiler offline) |

## CCMM XML import / export

### Pipeline

```
import:  CCMM XML --(xmlschema, XSD validation)--> generic JSON --DatasetSchema.load--> record dict --> RDM service
export:  record (service result, or search-index record for OAI) --CCMMXMLSerializer / DatasetSchema.dump--> generic JSON --> CCMM XML (XSD validated, best effort)
```

* Import: `CCMMJSONDeserializer` (resources/deserializers/ccmm.py) is registered as the `ccmm-xml` import
  (`application/vnd.ccmm+xml`). An invalid XML document is a 400; the loaded dict
  goes to the service as the create payload (`metadata`, `ccmm_xml`, `access`, `files`).
* Export: `CCMMXMLSerializer` is the `ccmm-xml` export (also OAI-PMH, prefix `ccmm`). Export is
  best effort - XSD errors are logged as warnings, not raised.
* The whole source XML is kept on the record in `ccmm_xml` (root field, copied between draft and
  record on publish / edit / new version by `RootRecordComponent`).
* The model also registers the RDM complete exports (`RDMCompleteExportsPreset` - dublincore,
  datacite-json, geojson, csl, bibtex, jsonld, csv, datapackage, citation; the metadata is a
  superset of what they need). `marcxml`, `dcat` and `datacite-xml` are registered but fail on
  the expanded subject titles (subjects dump as `{"id"}` only, no title) until oarepo-rdm
  expands the subjects relation - see the known gaps. Import is json + ccmm-xml (no ro-crate).

### The schemas (`resources/serializers/ccmm/schema/`)

| Module | Converts |
|---|---|
| `dataset.py` | record level: `DatasetSchema` (`metadata`, `ccmm_xml`, access rights), `DatasetMetadataSchema` (the metadata), `CommonResourceFieldsMixin`, `RelatedResourceSchema`, and the dataset's own titles/descriptions |
| `fields.py` | shared marshmallow plumbing (`SplitNested`, `LanguageTextMixin`/`MultilingualField` & friends, `IriLabelSchema`, `ApplicationProfileSchema`) |
| `identifiers.py` | identifier/scheme, award identifiers, `service_item_exists`/`vocabulary_item_exists` |
| `agents.py` | persons/organizations & roles ↔ RDM creators, contributors, publisher |
| `time_references.py` | time references ↔ RDM EDTF dates |
| `terms_of_use.py` | terms of use (license) ↔ RDM rights |
| `funding.py` | funding reference ↔ RDM funding (funder, award) |
| `subjects.py` | subjects ↔ RDM subjects/keywords |
| `locations.py` | locations ↔ RDM GeoJSON features (GML/WKT → WGS84) |
| `distribution.py` | distributions (data services, downloadable files; CCMM-shaped in the model), `DistributionsField`, `file_distributions` (uploaded files → distributions) |
| `metadata_record.py` | `metadata_identification` (stored or generated) |
| `access.py` | CCMM access rights ↔ RDM record `access` |
| `vocabs.py` | `CCMMVocabularyField` (CCMM `{iri, label}` ↔ invenio `{id}`), `XMLLangField` |
| `urls.py` | `is_local_url` (SITE_UI_URL / SITE_API_URL) |

Conventions in the schemas:

* **Field name = the invenio field, `data_key` = the CCMM element.** Each field has a comment with
  its CCMM cardinality (`# ccmm 0..n`). Unmapped CCMM elements are listed in comments
  ("no counterpart in invenio") and excluded via `Meta.unknown = EXCLUDE`.
* The schemas were **written from scratch** against the XSD and the model - do not port old
  parser code as a reference.
* Keep functionality **out of `DatasetMetadataSchema`** where possible: prefer a dedicated field
  (e.g. `DistributionsField`, `SplitNested`) or the record-level `DatasetSchema` over more hooks
  on the metadata schema.
* `load_default` of mutable values must be a callable (`lambda: {"id": "other"}`), otherwise the
  same dict is shared by all loads.

### Mapping decisions (the non-obvious ones)

| CCMM | Invenio | Notes |
|---|---|---|
| vocabulary items `{iri, label}` | `{id}` | looked up in the SKOS mappings (`exactMatch`, `narrowMatch`), **strict** - an unknown IRI is a validation error. With `id_prefix`, an IRI in the vocabulary namespace is also looked up by the lower-cased rest (`…/file-type/TAR` → `tar`). Export writes the IRI from the `exactMatch` mapping and the labels from the vocabulary |
| `xml:lang=""` in multilingual fields | language `und` (Undetermined) | dumped back as `xml:lang=""`; `und` is added to `languages_primary` |
| `qualified_relation` | `creators` (Creator), `publisher` (Publisher, a string), `contributors` (other roles) | publisher: names joined by `", "`, exported as one organization |
| `metadata_identification` | `metadata.metadata_identifications` (`CCMMInvenioMetadataRecord`, agents as RDM contributors) | **stored as it came** (harvested records) and exported **without changes**. Without a stored one (records created here) it is generated from `created`/`updated`/`links`; contributors with role `datamanager` are copied into it (and stay contributors), otherwise the repository (`THEME_SITENAME`) is the Data Manager. Not in the UI yet |
| `terms_of_use/access_rights` | record `access` (+ `files.enabled` for metadata-only) | `open` / `restricted` / `metadata-only` / `embargoed` (= RDM access status ids). Embargo end = the "Available" date; export uses `access.status`. See `access.py` |
| `terms_of_use/license` (+ description) | `rights` | RDM rejects a description next to a vocabulary license - it is dropped then |
| `iri` (dataset, related resource), `resource_url` | stored as they are | not converted to identifiers |
| `related_resource` | `related_resources` (`CCMMInvenioRelatedResource`) | related resource without a title gets the iri / resource url as title (required in the model) |
| — | `related_identifiers` | **derived** from `related_resources` by `RelatedIdentifiersComponent` on create/update (overwrites whatever the client sent), validated with RDM's `RelatedIdentifierSchema`. Hidden from the `application/json` API (the UI JSON keeps them); DataCite registration uses the record, not the response |
| `distribution` | `distributions` (CCMM-shaped) | a downloadable file with an access/download url on this server is **not loaded** (it is an uploaded file). On export the record's **uploaded files are added** as downloadable files - only those the reader may see (REST: `files.entries` exist only with `read_files`; OAI: only public record + public files; hidden files never) |
| `subject` | `subjects` | vocabulary subject (FORD, INSPIRE themes) → `{id}`, otherwise a keyword per language variant. Export adds `classification_code` (vocabulary prop, or the id without the scheme prefix) and the scheme name |
| funder / affiliation | RDM funder / affiliation (`id`, `name`) | the id is set when the ROR is in the funders / affiliations vocabulary; other identifiers are dropped (RDM does not accept them) |
| `location` | RDM `locations` (GeoJSON features, WGS84) | GML is reprojected; a multi-polygon is split |
| `resource_type` missing | `dataset` | RDM requires a resource type |
| `publication_year` | `publication_date` | the "Created" time reference wins, else `<year>-01-01` |

## Vocabularies

* The fixtures in `src/ccmm_invenio/fixtures/` are **generated** by
  `python -m ccmm_invenio.fixtures.compiler.converter` (`scripts/compile_vocabularies.sh`).
  The script **wipes the directory and refetches every source over the network** - upstream
  data may have drifted, so review the diff of every file.
* To change a few vocabularies, regenerate only those with the converter functions
  (`vocabulary_builders()[name]()` → `export_vocabulary` / `export_subjects` + `export_turtle`,
  and `export_vocabulary_index` for `vocabularies.yaml`; all in `fixtures/compiler/`) and check the diff is what you expect.
  Never hand-edit a generated fixture without fixing its source (reader or `fixtures/input/vocabularies/`)
  as well.
* Subjects: one data file per scheme - `subjects.yaml` (FORD) and `subjects_inspire.yaml`
  (INSPIRE themes); schemes are declared in `VOCABULARY_SCHEMES` (`fixtures/compiler/converter.py`). Entries carry
  `props.classification_code`.
* `languages_primary` (the loaded `languages`) = ISO 639-1 subset + `und`.
* Test fixture loading: use `VocabulariesFixture(system_identity, FIXTURES / "vocabularies.yaml")`
  (as `tests/test_ccmm_import_http.py` does) - it knows the type aliases and the subjects
  service. Funders / affiliations (ROR) are not fixtures; tests create the ones they need.

## Sample data

`ccmm_versions/ccmm-xml-releases/<version>/metadata-samples/xml/*.xml` are reference data for the
tests. **When a sample has a
data error, fix the sample** (with a comment if the reason is not obvious) instead of making the
conversion lenient - vocabulary lookups stay strict. Errors fixed so far: wrong/non-canonical
vocabulary IRIs (file type as media type, web page instead of the authority IRI, trailing
slashes, the INSPIRE scheme IRI), an empty required `<iri/>`, a wrong checksum algorithm, a
metadata IRI outside its original repository.

## Working on the code

* Run the tests with the project virtualenv: `.venv/bin/pytest tests` (services from
  `.env-services`; see `run.sh`). The full suite takes ~2.5 minutes; the HTTP tests
  (`test_ccmm_import_http.py`, `test_ccmm_file_distributions.py`) are the slow ones.
* Lint / format: `.venv/bin/ruff check src tests` and `.venv/bin/ruff format src tests`
  (line length 120).
* **Throwaway probes**: when inspecting data through a pytest probe, write the results to a file
  (e.g. `/tmp/<name>.json`) and read it afterwards - the output of a passing test is discarded.
  Delete the probe afterwards.
* A useful check after conversion changes: import `ccmm_sample.xml` over REST, export it again and
  diff the two generic JSONs (see the known gaps below for the expected differences).
* When updating a draft in tests with JSON read from the API, drop the affiliation `identifiers`
  expanded from the vocabulary (`drop_expanded_affiliation_identifiers` in the HTTP tests) - they
  are dump-only in RDM.
* OARepo model customizations: presets are ordered by `provides` / `depends_on` / `modifies`.
  A preset modifying two targets can create a cycle (e.g. `exports` and `JSONUISerializer`) -
  split it. To change an existing export, use `ReplaceExportSerializer` (`models/customizations.py`).

## Known gaps and open items

Remaining differences of a CCMM XML → record → CCMM XML round trip (`ccmm_sample.xml`):

* **Personal data not stored**: `contact_point` of persons, of the metadata record's agents and of
  `terms_of_use`.
* **Publisher** is an RDM string: a person publisher (ORCID, given/family name) becomes an
  organization with the name only. Options discussed: publisher as a contributor with the
  `publisher` role, or wait for the structured publisher (DataCite 4.7).

* **Local identifier schemes** become `url` with the full IRI as the value.
* **Locations**: the original GML / CRS and `bounding_box` are not kept; the related object
  `title` has no RDM field (`place` holds the location name).
* **terms_of_use description** is dropped with a vocabulary license.
* **Subjects**: definitions are not stored; the scheme label is English only; keywords lose their
  language.
* **Cosmetic**: vocabulary labels come from our vocabularies (order / wording differ), person
  names are rebuilt by RDM ("Novák, Jan"), `xml:lang=""` on identifier-scheme labels becomes `en`,
  WKT whitespace is normalised.
* Considered, not done: export the stored `ccmm_xml` as-is for records not edited since import
  (lossless for harvested records); fill RDM-less details back from `ccmm_xml` after edits.
* **Subjects are not expanded** in the record dump (the `{id}` only, no title), so the RDM
  exports that index `subject["subject"]` (`marcxml`, `dcat`, `datacite-xml`) 500 on records
  with subjects. The expansion (the subjects relation of `RDMSubject` in oarepo-rdm) is being
  fixed upstream; `tests/test_rdm_exports.py` guards the flip (strict xfail → remove
  `NEEDS_SUBJECT_EXPANSION` then).
* The UI does not show / edit `metadata_identifications` yet; `related_identifiers` should not be
  editable in the deposit form (it is derived and overwritten).

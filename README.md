# CCMM-Invenio: CCMM runtime library for NRP Invenio

This library provides:

* an OARepo model preset for CCMM datasets (`ccmm_preset_1_1_0`)
* CCMM XML import and export (REST, OAI-PMH)
* vocabulary fixtures for the CCMM model
* UI components for working with the CCMM model in NRP Invenio
* prefilling related resources from a DOI or Handle (the CCMM mappings of
  [oarepo-related-resources](#related-resources-prefill-from-a-doi-or-handle))

## Installation

```bash
pip install ccmm-invenio
```

## Usage

To use CCMM in a repository, add the following model:

```python
# models/datasets.py
from ccmm_invenio.models import ccmm_preset_1_1_0

ccmm_dataset = model(
    "ccmm_dataset",
    version="1.1.0",
    presets=[
        ccmm_preset_1_1_0,
    ],
    configuration={
        # "ui_blueprint": "myui
    },
    types=[
        {
            "Metadata": {
                "properties": {
                    # your extensions come here, ccmm_preset_1_1_0 will add
                    # all ccmm fields automatically
                },
            },
        }
    ],
    metadata_type="Metadata",
    customizations=[],
)

# invenio.cfg
ccmm_dataset.register()
```

`ccmm_production_preset_1_1_0` is an alias of `ccmm_preset_1_1_0`.

The preset adds the CCMM XML import and export (`application/vnd.ccmm+xml`,
also OAI-PMH with the `ccmm` metadata prefix).

## Design

### One model, RDM based

`ccmm_preset_1_1_0` is the only model. It uses the InvenioRDM field types wherever RDM has an
equivalent and CCMM-shaped types (distributions, related resources, metadata records, …) for the
rest, so the RDM features - DataCite DOI registration, search, the landing page, access, files -
keep working. CCMM-only data is added next to the RDM data, not instead of it.

The model can also hold **harvested 3rd party records**: their CCMM `metadata_identification` is
stored as it came and exported unchanged.

### CCMM XML import and export

```
import:  CCMM XML --(XSD validation)--> generic JSON --> record --> RDM service
export:  record --> generic JSON --> CCMM XML (XSD validated, best effort)
```

* An XML document that is not valid against the CCMM XSD is rejected (HTTP 400). Vocabulary items
  are matched strictly by their IRI - an unknown IRI is a validation error.
* The whole source XML is kept on the record in the `ccmm_xml` field, so nothing of an imported
  document is lost even where the conversion is lossy.
* Export is best effort: an XSD error of the exported document is logged as a warning. Elements
  CCMM requires but the record does not have get fallbacks (the record PIDs and landing page as
  identifiers, the creation date, a placeholder subject and license).
* Besides CCMM XML, records can be imported as JSON and DataCite JSON
  (`application/vnd.datacite.datacite+json`), and exported in the RDM formats (DataCite JSON,
  Dublin Core, CSL, BibTeX, JSON-LD, GeoJSON, …).
* RDM `related_identifiers` are derived from the CCMM `related_resources` on every create/update
  (whatever a client sends in them is overwritten).

The differences between CCMM and the Invenio record - what is converted, modified or dropped on
import and export - are described on the *CCMM support in Invenio(RDM)* page of the
documentation (`docs/ccmm.md`).

### Vocabularies

The vocabulary fixtures (`src/ccmm_invenio/fixtures/`) are generated from the CCMM, COAR,
DataCite, EU, IANA, INSPIRE, RDM, … sources by the fixture compiler
(`scripts/compile_vocabularies.sh`); they are registered through the
`invenio_rdm_records.fixtures` entry point. Each item carries SKOS mappings to the IRIs CCMM uses -
they drive the IRI matching of the import and the IRIs of the export. Funders and affiliations
(ROR) are not part of the fixtures.

### ARK identifiers (idutils patch)

idutils, used by RDM to detect, validate and resolve identifiers, does not handle `https` ARK URLs
(`https://n2t.net/ark:/…`) yet. Until it does upstream, importing `ccmm_invenio` patches it for the
whole process: `https` ARK URLs are valid ARKs, they are normalized to `ark:/…`, and their landing
URL is `https://n2t.net/ark:/…`. The patch disables itself once idutils supports this.

## Related resources (prefill from a DOI or Handle)

Instead of typing a related resource (a publication, a software, another dataset, …) by hand,
a depositor can load its metadata from its persistent identifier. In the deposit form, the
*Related resources* field has a **Load from DOI** button: paste one or more DOIs or Handles
(with or without the `https://doi.org/` / `https://hdl.handle.net/` prefix), pick the
relation type and the resources are added to the record, prefilled. Problems (values that
could not be mapped) are shown as warnings next to the imported item; the depositor reviews
and completes the item before saving.

### How it works

The work is split between two packages:

* [oarepo-related-resources](https://github.com/oarepo/oarepo-related-resources) (a
  dependency, installed automatically) provides the `POST /api/related-records` endpoint and
  the **resolvers** - they recognize the identifier and fetch its metadata from the registry.
  It knows nothing about the record shape.
* ccmm-invenio provides the **mappings** of the fetched metadata to the CCMM record metadata
  (`ccmm_invenio.related_resources`) and plugs them into the resolvers through configuration.

```
identifier --> resolver (fetch) --> CCMM mapping --> related resource metadata (+ problems)
```

The resolvers are tried in order (`RELATED_RESOURCES_PERSISTENT_IDENTIFIER_RESOLVERS`); the
first one that recognizes the identifier and finds it in its registry is used - so a DOI is
looked up at DataCite first and at Crossref if DataCite does not know it.

| Resolver | Fetches | The CCMM mapping fills in |
|---|---|---|
| DataCite | the DOI's DataCite attributes (REST API) | title, additional titles, creators and contributors (with affiliations, ORCIDs), publisher, publication date, dates, resource type, subjects, language, descriptions, related identifiers, identifiers, rights, sizes, formats, version |
| Crossref | the DOI's Crossref work (REST API) | title, creators (with ORCIDs), publisher, publication date, abstract (JATS converted to text); resource type `dataset` |
| Handle | the landing page the Handle resolves to | title, creators, publication date (free-form dates are parsed, with a warning), abstracts (`DCTERMS.abstract`); resource type `dataset` |

Values are mapped to the repository vocabularies (resource types, languages, relation types,
licenses, …); a value that can not be mapped is left out and reported as a problem, the rest of
the resource is kept. The DataCite mapping is also used by the record-level DataCite JSON import
(`application/vnd.datacite.datacite+json`).

### Setup

Nothing needs to be configured: the extension is registered by its entry points and
ccmm-invenio's `invenio_config.module` (`ccmm_invenio/initial_config.py`) sets the hooks. They
are config defaults, so `invenio.cfg` can override any of them:

| Config | ccmm-invenio sets | Purpose |
|---|---|---|
| `RELATED_RESOURCES_DATACITE_MAPPER` | `ccmm_invenio.related_resources.datacite:map_datacite` | DataCite attributes → CCMM metadata |
| `RELATED_RESOURCES_CROSSREF_MAPPER` | `ccmm_invenio.related_resources.crossref:map_crossref` | Crossref work → CCMM metadata |
| `RELATED_RESOURCES_HANDLE_MAPPER` | `ccmm_invenio.related_resources.handle:map_handle` | Handle landing page → CCMM metadata |
| `RELATED_RESOURCES_RECORD_UI_SCHEMA` | `ccmm_invenio.resources.serializers.ui.related_resources.CCMMRelatedResourceUISchema` | UI serialization of the result (what the deposit form gets) |
| `RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE` | `dataset` | resource type when the source has none or an unknown one |

Settings of oarepo-related-resources itself you may want to change in `invenio.cfg`:

* `RELATED_RESOURCES_PERMISSION_POLICY` - who may use the endpoint (default: any
  authenticated user),
* `RELATED_RESOURCES_PERSISTENT_IDENTIFIER_RESOLVERS` - the resolvers and their order (default:
  DataCite, Crossref, Handle),
* `DATACITE_URL`, `CROSSREF_URL`, `HANDLE_URL`, `RELATED_RESOURCES_DEFAULT_TIMEOUT` - the
  registry endpoints and the request timeout (seconds),
* `ORCID_AWS_ACCESS_KEY_ID`, `ORCID_AWS_SECRET_ACCESS_KEY` (and
  `ORCID_PUBLIC_DUMP_S3_BUCKET_NAME`) - access to the ORCID public data dump. The DataCite
  mapping turns a creator's ORCID into an entry of the `names` vocabulary: an existing entry is
  reused, a new one is created from the dump. **Set them** if you want ORCIDs: without them the
  ORCID importer can not be created at all, so every ORCID (even one already in `names`) is
  logged as an error and left out - the person is imported without it.

### The API

The deposit form calls the endpoint for you; it can also be used directly (authenticated):

```bash
curl -X POST https://<repository>/api/related-records \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"identifier": "10.1575/1912/1099"}'
```

```json
{
  "metadata": {
    "title": "Observations of vertical humidity distribution above the ocean surface and their relation to evaporation",
    "creators": [
      {"person_or_org": {"name": "Montgomery, Raymond B.", "type": "personal",
                         "given_name": "Raymond B.", "family_name": "Montgomery"}}
    ],
    "publisher": "Massachusetts Institute of Technology and Woods Hole Oceanographic Institution",
    "publication_date": "1940",
    "resource_type": {"id": "dataset"}
  },
  "import_errors": [],
  "validation_errors": []
}
```

* `import_errors` - the problems of the resolver and the mapping (`resolver`, `message`,
  `level`: `info` / `warning` / `error`); they do not fail the request,
* `validation_errors` - errors of loading the metadata into the record schema
  (`RELATED_RESOURCES_RECORD_SCHEMA`),
* HTTP errors: `403` not allowed, `404` an unsupported identifier or one the registry does not
  know, the registry's status when the registry request fails, `500` an unexpected error.

### Customizing the mapping

To change what is imported, point the `RELATED_RESOURCES_<PROVIDER>_MAPPER` config to your own
callable `(fetched metadata) -> (metadata, list[ResolverProblem])` - e.g. a subclass of the
CCMM mapping:

```python
# my_repository/related_resources.py
from oarepo_related_resources.resolvers.utils import handle_errors

from ccmm_invenio.related_resources.crossref import CrossrefMapping


class MyCrossrefMapping(CrossrefMapping):
    def resolve_metadata(self):
        super().resolve_metadata()
        self.resolve_container_title()
        return self.processed_metadata, self.problems

    @handle_errors()
    def resolve_container_title(self): ...


def map_crossref(work):
    return MyCrossrefMapping(work).resolve_metadata()


# invenio.cfg
RELATED_RESOURCES_CROSSREF_MAPPER = "my_repository.related_resources:map_crossref"
```

The mappings are subclasses of `oarepo_related_resources.resolvers.ResolverMapping`; see the
oarepo-related-resources README for writing one from scratch.

## How to adapt to a new CCMM version

### Download and pre-process CCMM XML

Follow the instructions in `ccmm_versions/README.md` to download and pre-process
the CCMM XML schemas for the desired version. This will create:

* Cleaned XSD files in `ccmm_versions/src/ccmm_versions/ccmm-<version>-<date>/out`
* A diff file in `ccmm_versions/diffs/` comparing the new version to the previous one
* A schema overview in `ccmm_versions/summaries/ccmm-<version>-<date>.summary.md`

### Adapt the model yaml files

Copy the model in `src/ccmm_invenio/models/<previous-version>-<date>/` to
`src/ccmm_invenio/models/<new-version>-<date>/`.

Look at the diff file generated in the previous step and adapt the
`ccmm.yaml` (the CCMM types used by the model), `ccmm-invenio.yaml` (the dataset, RDM based)
and `ccmm-vocabularies.yaml` files in `src/ccmm_invenio/models/<version>-<date>/` accordingly.

Then add the new version to `src/ccmm_invenio/models/__init__.py`, the new XSD to
`src/ccmm_invenio/resources/serializers/ccmm/xsd/` (updating the path in
`converter.py`) and adapt the marshmallow schemas in
`src/ccmm_invenio/resources/serializers/ccmm/schema/`.

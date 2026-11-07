# CCMM-Invenio: CCMM runtime library for NRP Invenio

This library provides:

* an OARepo model preset for CCMM datasets (`ccmm_preset_1_1_0`)
* CCMM XML import and export (REST, OAI-PMH)
* vocabulary fixtures for the CCMM model
* UI components for working with the CCMM model in NRP Invenio

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

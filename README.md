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

The preset adds the CCMM XML import and export (`application/vnd.ccmm.research-data+xml`,
also OAI-PMH with the `ccmm` metadata prefix). See [AGENTS.md](AGENTS.md) for the design of the
model and of the CCMM conversion.

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

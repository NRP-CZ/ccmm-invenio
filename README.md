# CCMM-Invenio: CCMM runtime library for NRP Invenio

This library provides:

* Fixtures for vocabularies to support the CCMM model in NRP Invenio
* Schema serializers for the CCMM model
* Import and export modules for the CCMM model
* UI components for working with the CCMM model in NRP Invenio

## Installation

```bash
pip install ccmm-invenio
```

## Usage

To use CCMM in production repository, add the following model:

```python
# models/datasets.py
production_dataset = model(
    "production_dataset",
    version="1.1.0",
    presets=[
        ccmm_production_preset,
    ],
    configuration={
        # "ui_blueprint": "myui
    },
    types=[
        {
            "Metadata": {
                "properties": {
                    # your extensions come here, ccmm_production_preset will add 
                    # all ccmm fields automatically
                },
            },
        }
    ],
    metadata_type="Metadata",
    customizations=[],
)

# invenio.cfg
production_dataset.register() 
```

## How to generate new NMA and Production CCMM model mappings

### Download and pre-process CCMM XML

Follow the instructions in `ccmm_versions/README.md` to download and pre-process
the CCMM XML schemas for the desired version. This will create:

* Cleaned XSD files in `ccmm_versions/src/ccmm_versions/ccmm-<version>-<date>/out`
* A diff file in `ccmm_versions/diffs/` comparing the new version to the previous one
* A schema overview in `ccmm_versions/summaries/ccmm-<version>-<date>.summary.md`

### Adapt CCMM model yaml files

Copy/paste the model in `src/ccmm_invenio/models/<previous-version>-<date>/` to
`src/ccmm_invenio/models/<new-version>-<date>/`. 

Look at the diff file generated in the previous step and adapt the
`ccmm.yaml`, `ccmm-invenio.yaml`, `ccmm-vocabularies.yaml`, and `gml-1.1.0.yaml` files
in `src/ccmm_invenio/models/<version>-<date>/` accordingly.

Then look at the `src/ccmm_invenio/models/__init__.py` file and add the new version
there.

### Generate NMA Parser

```bash

CCMM_VERSION_DIR=1.1.0a1-2025-10-25
CCMM_VERSION=1.1.0

python ./src/ccmm_invenio/parsers/generate_parser.py  \
       ./src/ccmm_invenio/models/$CCMM_VERSION_DIR/ccmm.yaml \
       ./src/ccmm_invenio/models/$CCMM_VERSION_DIR/ccmm-vocabularies.yaml \
       ./src/ccmm_invenio/models/$CCMM_VERSION_DIR/gml-1.1.0.yaml \
       ./src/ccmm_invenio/parsers/nma_$(echo "$CCMM_VERSION" | tr "." "_")$.py
```

### Update production parser manually based on NMA parser

```python

# file production_<version>.py
from .nma_<version> import CCMMXMLNMAParser

class CCMMXMLProductionParser(CCMMXMLProductionParserBase, CCMMXMLNMAParser):
    """Parser for CCMM XML version 1.1.0 for production repository."""
    # tweaks here
```

## TODO: imports, exports

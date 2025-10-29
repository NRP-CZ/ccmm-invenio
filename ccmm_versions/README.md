# CCMM Versions

This directory contains versioned releases of the CCMM XML schemas.
We are keeping these version for references and comparison purposes
as CCMM XML schemas evolve over time and their versioning is not
a standard semantic versioning.

## Adding a new version

To add a new version of the CCMM XML schemas, run the `add_ccmm.sh` script located in scripts folder:

```bash
scripts/add_ccmm.sh <version> <which-tag-to-checkout>

Example:
scripts/add_ccmm.sh 1.1.0 master
```

This will create a new folder `ccmm-<version>-<date>` in this directory. Then, it
cleans up the xsd files and writes the clean ones into the `ccmm-<version>-<date>/out`
folder. Then it will generate a diff to the previous version and store it in the
`diffs` folder.

## Creating schema overview

To create an overview of the schema types in a given directory, you can use the `create_schema_overview.py` script located in the `ccmm_versions/src/ccmm_versions/` folder.

```bash

python ccmm_versions/src/ccmm_versions/create_schema_overview.py ccmm-xml-releases/<schema_dir>/out <output_markdown_file>
```

#!/usr/bin/env bash
#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
# Compile the Invenio vocabulary fixtures from their sources.
#
# Runs the vocabulary conversion pipeline
# (ccmm_invenio.fixtures.compiler.converter) and (re)creates the
# content of src/ccmm_invenio/fixtures: the vocabularies.yaml index at its
# root (where the RDM extension fixture loader looks for it) and the Invenio
# YAML fixtures with the turtle serializations of their graphs in data/.
# The files are wiped first (except the package __init__.py), so the
# fixtures of vocabularies that are no longer exported do not linger.
#
# Needs the compile-vocabularies extras
# (pip install -e '.[compile-vocabularies]') and network access to the
# vocabulary sources (CCMM, COAR, DataCite, EU, IANA, ...).

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$repo_root"

source .venv/bin/activate

fixtures_dir="src/ccmm_invenio/fixtures"

# remove the fixtures of the previous runs; keep the package marker
find "${fixtures_dir}" -maxdepth 1 -type f ! -name '__init__.py' -delete
rm -rf "${fixtures_dir}/data"

python -m ccmm_invenio.fixtures.compiler.converter "${fixtures_dir}"

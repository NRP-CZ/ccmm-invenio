#!/bin/bash
set -e

OAREPO_VERSION=${OAREPO_VERSION:-12}
PYTHON=${PYTHON:-python3}
export PIP_EXTRA_INDEX_URL=https://gitlab.cesnet.cz/api/v4/projects/1408/packages/pypi/simple
export UV_EXTRA_INDEX_URL=https://gitlab.cesnet.cz/api/v4/projects/1408/packages/pypi/simple

TEST_VENV=${TEST_VENV:-.venv-tests}

$PYTHON -m venv $TEST_VENV

source $TEST_VENV/bin/activate
pip install --upgrade pip setuptools wheel

pip install -e '.[tests]'
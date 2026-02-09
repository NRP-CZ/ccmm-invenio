#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of oarepo-model (see https://github.com/oarepo/oarepo-model).
#
# oarepo-model is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

import logging
import re
from typing import Any

import pytest
from flask_principal import Identity, Need, UserNeed
from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as current_vocabularies_service
from oarepo_runtime.services.records.mapping import update_all_records_mappings

from tests.model import nma_dataset, production_dataset  # noqa: F401

log = logging.getLogger("tests")

pytest_plugins = ("celery.contrib.pytest",)


@pytest.fixture(scope="module")
def app_config(
    app_config,
):
    """Override pytest-invenio app_config fixture.

    Needed to set the fields on the custom fields schema.
    """
    app_config["FILES_REST_STORAGE_CLASS_LIST"] = {
        "L": "Local",
    }

    app_config["FILES_REST_DEFAULT_STORAGE_CLASS"] = "L"

    app_config["RECORDS_REFRESOLVER_CLS"] = "invenio_records.resolver.InvenioRefResolver"
    app_config["RECORDS_REFRESOLVER_STORE"] = "invenio_jsonschemas.proxies.current_refresolver_store"

    app_config["THEME_FRONTPAGE"] = False

    app_config["SQLALCHEMY_ENGINE_OPTIONS"] = {  # avoid pool_timeout set in invenio_app_rdm
        "pool_pre_ping": False,
        "pool_recycle": 3600,
    }

    # disable CSRF protection for tests
    app_config["REST_CSRF_ENABLED"] = False

    app_config["RDM_PERSISTENT_IDENTIFIERS"] = {}

    app_config["RDM_OPTIONAL_DOI_VALIDATOR"] = lambda _draft, _previous_published, **_kwargs: True

    app_config["DATACITE_TEST_MODE"] = True
    app_config["RDM_RECORDS_ALLOW_RESTRICTION_AFTER_GRACE_PERIOD"] = True

    # for RDM links
    app_config["IIIF_FORMATS"] = ["jpg", "png"]
    app_config["APP_RDM_RECORD_THUMBNAIL_SIZES"] = [500]
    app_config["RDM_ARCHIVE_DOWNLOAD_ENABLED"] = True

    return app_config


@pytest.fixture(scope="module")
def identity_simple():
    """Create simple identity fixture."""
    i = Identity(1)
    i.provides.add(UserNeed(1))
    i.provides.add(Need(method="system_role", value="any_user"))
    i.provides.add(Need(method="system_role", value="authenticated_user"))
    return i


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture."""
    from invenio_app.factory import create_api as _create_api

    return _create_api


@pytest.fixture(scope="module")
def extra_entry_points():
    return {
        "invenio_base.blueprints": [],
    }


@pytest.fixture(scope="module")
def search(search):
    """Search fixture."""
    update_all_records_mappings()
    return search


@pytest.fixture(scope="module")
def clean_strings():
    def _clean_strings(s: Any) -> Any:
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        if isinstance(s, str):
            # strip the string, replace sequences of 1+ whitespaces with a single space
            return re.sub(r"\s+", " ", s.strip())
        if isinstance(s, list):
            return [_clean_strings(item) for item in s]
        if isinstance(s, dict):
            return {key: _clean_strings(value) for key, value in s.items()}
        return s

    return _clean_strings


@pytest.fixture
def vocab_fixtures():
    """Contributor role fixture."""
    current_vocabularies_service.create_type(system_identity, "resourcetypes", "rsrct")

    current_vocabularies_service.create(
        system_identity,
        {
            "type": "resourcetypes",
            "id": "dataset",
            "title": {
                "en": "Dataset",
                "cs": "Dataset",
            },
        },
    )

    current_vocabularies_service.indexer.refresh()

# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""The temporary ARK support of idutils (ccmm_invenio.idutils_ark)."""

from __future__ import annotations

import idutils
import pytest
from invenio_rdm_records.config import RDM_RECORDS_IDENTIFIERS_SCHEMES

import ccmm_invenio  # noqa: F401 - applies the patch
from ccmm_invenio.idutils_ark import patch_idutils_ark

ARK = "ark:/13030/tf5p30086k"


@pytest.mark.parametrize(
    "value",
    [ARK, "ark:13030/tf5p30086k", f"https://n2t.net/{ARK}", f"http://n2t.net/{ARK}", f"https://example.org/{ARK}"],
)
def test_is_ark(value):
    assert idutils.is_ark(value)
    # the validator RDM captured at import time is patched as well
    assert RDM_RECORDS_IDENTIFIERS_SCHEMES["ark"]["validator"](value)


@pytest.mark.parametrize(
    "value", ["https://n2t.net/", "https://example.org/ark", "10.1234/abc", f"ftp://n2t.net/{ARK}"]
)
def test_not_ark(value):
    assert not idutils.is_ark(value)


def test_detect_https_ark():
    # the most specific scheme first - ccmm's fallback_scheme takes the first one
    assert idutils.detect_identifier_schemes(f"https://n2t.net/{ARK}") == ["ark", "url"]
    assert idutils.detect_identifier_schemes(ARK) == ["ark"]


@pytest.mark.parametrize(
    ("value", "normalized"),
    [
        (f"https://n2t.net/{ARK}", ARK),
        (f"http://example.org/{ARK}", ARK),
        (f"https://n2t.net/{ARK}?info", f"{ARK}?info"),
        (f" {ARK} ", ARK),
        ("ark:13030/tf5p30086k", "ark:13030/tf5p30086k"),
    ],
)
def test_normalize_ark(value, normalized):
    assert idutils.normalize_pid(value, "ark") == normalized


def test_ark_url():
    assert idutils.to_url(ARK, "ark", url_scheme="https") == f"https://n2t.net/{ARK}"
    assert idutils.to_url(f"https://example.org/{ARK}", "ark", url_scheme="https") == f"https://n2t.net/{ARK}"


def test_other_schemes_unchanged():
    assert idutils.normalize_pid("https://doi.org/10.1234/abc", "doi") == "10.1234/abc"
    assert idutils.to_url("10.1234/abc", "doi", url_scheme="https") == "https://doi.org/10.1234/abc"
    assert idutils.detect_identifier_schemes("https://example.org/x") == ["url"]


def test_patch_idempotent():
    patch_idutils_ark()
    patch_idutils_ark()
    assert idutils.normalize_pid(f"https://n2t.net/{ARK}", "ark") == ARK

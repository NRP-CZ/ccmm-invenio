#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ARK support for idutils - a temporary monkeypatch until it is done upstream.

idutils (1.7.0) knows the ``ark`` scheme only partially:

* ``is_ark`` accepts an ARK URL only with ``http`` - ``https://n2t.net/ark:/13030/x``, the form CCMM
  records carry, is not an ARK (it is detected as ``url`` and RDM rejects it as an ``ark`` identifier),
* ``normalize_pid`` has no ARK normalizer (the resolver URL stays in the value),
* ``to_url`` has no ARK landing URL (it returns ``""``, so the CCMM export has no identifier iri).

The ``idutils.custom_schemes`` entry point can not help - it only adds new schemes, ``ark`` is a
built-in one. So:

* the code of ``idutils.validators.is_ark`` is replaced in place - the function object is captured
  at import time elsewhere (``invenio_rdm_records.config.RDM_RECORDS_IDENTIFIERS_SCHEMES``, the
  idutils scheme list, ``idutils.is_ark``), only a code swap reaches them all,
* the normalizer and the URL generator are added as an ``ark`` entry of the idutils custom scheme
  registry - ``normalize_pid`` and ``to_url`` fall through to it for the schemes they do not handle
  themselves (its validator never matches, detection is done by the patched ``is_ark``).

Each part is applied only while idutils still lacks it, so the patch retires itself once upstream
handles ARK - remove this module then.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from idutils import normalizers, validators
from idutils.proxies import custom_schemes_registry
from idutils.utils import ark_suffix_regexp

ARK_RESOLVER = "n2t.net"
"""The ARK resolver the landing URLs point to (also the resolver of the CCMM ARK scheme IRI)."""

_PROBE_URL = "https://n2t.net/ark:/13030/tf5p30086k"
_PROBE_ARK = "ark:/13030/tf5p30086k"


def _is_ark(val: Any) -> bool:
    """Test if argument is an ARK (a bare ``ark:`` one or an http(s) URL of one).

    Its code replaces the one of ``idutils.validators.is_ark``, it runs with that module's globals
    (``urlparse``, ``ark_suffix_regexp``) - use no other names.
    """
    res = urlparse(val)
    return bool(
        ark_suffix_regexp.match(val)
        or (
            res.scheme in ("http", "https")
            and res.netloc != ""
            # res.path includes the leading slash
            and ark_suffix_regexp.match(res.path[1:])
            and res.params == ""
        )
    )


def normalize_ark(val: str) -> str:
    """Normalize an ARK: an http(s) URL of it (any resolver) to the bare ``ark:...`` value."""
    val = val.strip()
    res = urlparse(val)
    if res.scheme in ("http", "https") and ark_suffix_regexp.match(res.path[1:]):
        # the path with the query (ARK inflections, e.g. "?info") and the fragment
        return val.split(res.netloc, 1)[1][1:]
    return val


def ark_url(url_scheme: str, pid: str) -> str:
    """Return the landing URL of a normalized ARK."""
    return f"{url_scheme}://{ARK_RESOLVER}/{pid}"


def patch_idutils_ark() -> None:
    """Add the missing ARK support to idutils (idempotent, skips what idutils already does)."""
    if not validators.is_ark(_PROBE_URL):
        validators.is_ark.__code__ = _is_ark.__code__

    registry: dict[str, dict[str, Any]] = custom_schemes_registry().custom_schemes
    if "ark" in registry:
        return
    config: dict[str, Any] = {}
    if normalizers.normalize_pid(_PROBE_URL, "ark") == _PROBE_URL:
        config["normalizer"] = normalize_ark
    if not normalizers.to_url(_PROBE_ARK, "ark"):
        config["url_generator"] = ark_url
    if config:
        registry["ark"] = {
            # the validator of a custom scheme is used for detection, the patched is_ark does that
            "validator": lambda _val: False,
            "normalizer": lambda val: val,
            "filter": [],
            "url_generator": lambda _url_scheme, _pid: None,
            **config,
        }

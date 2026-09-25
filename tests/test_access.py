#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ccmm_invenio.resources.serializers.ccmm.schema.access import access_right, rdm_access

TODAY = datetime.now(tz=UTC).date()
FUTURE = (TODAY + timedelta(days=30)).isoformat()
PAST = (TODAY - timedelta(days=30)).isoformat()


def available(date: str) -> list[dict]:
    return [{"date": "2024-05-01", "type": {"id": "created"}}, {"date": date, "type": {"id": "available"}}]


@pytest.mark.parametrize(
    ("ccmm_access_right", "dates", "access", "files"),
    [
        ("open", [], {"record": "public", "files": "public"}, None),
        ("restricted", [], {"record": "public", "files": "restricted"}, None),
        ("metadata-only", [], {"record": "public", "files": "public"}, {"enabled": False}),
        # embargoed until the Available date
        (
            "embargoed",
            available(FUTURE),
            {"record": "public", "files": "restricted", "embargo": {"active": True, "until": FUTURE}},
            None,
        ),
        # the embargo is over
        (
            "embargoed",
            available(PAST),
            {"record": "public", "files": "public", "embargo": {"active": False, "until": PAST}},
            None,
        ),
        # the end of the embargo is not known (no Available date, or not a day)
        ("embargoed", [], {"record": "public", "files": "restricted"}, None),
        ("embargoed", available("2030"), {"record": "public", "files": "restricted"}, None),
    ],
)
def test_rdm_access(ccmm_access_right, dates, access, files):
    assert rdm_access(ccmm_access_right, dates) == (access, files)


@pytest.mark.parametrize(
    ("access", "files", "expected"),
    [
        # the status computed by RDM wins
        ({"record": "public", "files": "public", "status": "metadata-only"}, None, "metadata-only"),
        # computed as RDM does, when there is no status
        ({"record": "public", "files": "public"}, {"enabled": True}, "open"),
        ({"record": "public", "files": "public"}, {"enabled": False}, "metadata-only"),
        ({"record": "public", "files": "restricted"}, {"enabled": True}, "restricted"),
        ({"record": "restricted", "files": "restricted"}, {"enabled": True}, "restricted"),
        ({"record": "public", "files": "restricted", "embargo": {"active": True, "until": FUTURE}}, None, "embargoed"),
    ],
)
def test_access_right(access, files, expected):
    assert access_right(access, files) == expected


@pytest.mark.parametrize("ccmm_access_right", ["open", "restricted", "metadata-only"])
def test_round_trip(ccmm_access_right):
    access, files = rdm_access(ccmm_access_right, [])
    assert access_right(access, files) == ccmm_access_right


def test_embargo_round_trip():
    access, files = rdm_access("embargoed", available(FUTURE))
    assert access_right(access, files) == "embargoed"

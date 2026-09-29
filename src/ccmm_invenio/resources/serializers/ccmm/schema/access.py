#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm access rights (terms_of_use/access_rights, COAR) <-> RDM record access.

The ids of the accessrights vocabulary are the RDM access statuses - open, embargoed,
restricted, metadata-only (see RecordAccess.status in invenio_rdm_records). The access
is on the record, not on the parent (the parent access has owners, grants and links).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


def rdm_access(access_right: str, dates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return the record access and files (None when not changed) for a ccmm access right.

    The metadata stay public in all cases, ccmm access rights describe the access to the data:

    open          - public record and files
    metadata-only - public record without files (files.enabled false, RDM has_files)
    restricted    - public record, restricted files
    embargoed     - public record, files restricted until the "Available" date of the dataset
                    (RDM embargo); with a past date the embargo is over (open), without it
                    the end is not known and the files are just restricted
    """
    if access_right == "open":
        return {"record": "public", "files": "public"}, None
    if access_right == "metadata-only":
        return {"record": "public", "files": "public"}, {"enabled": False}
    if access_right == "embargoed" and (until := _available_date(dates)):
        if until > datetime.now(tz=UTC).date():
            return {
                "record": "public",
                "files": "restricted",
                "embargo": {"active": True, "until": until.isoformat()},
            }, None
        return {"record": "public", "files": "public", "embargo": {"active": False, "until": until.isoformat()}}, None
    return {"record": "public", "files": "restricted"}, None


def access_right(access: dict[str, Any], files: dict[str, Any] | None) -> str:
    """Return the ccmm access right (accessrights vocabulary id) of an RDM record access.

    The status of the access (in the service result and the search index) is used,
    otherwise it is computed as RDM does.
    """
    if status := access.get("status"):
        return str(status)
    if (access.get("embargo") or {}).get("active"):
        return "embargoed"
    if access.get("record") == "public" and not (files or {}).get("enabled", True):
        return "metadata-only"
    if access.get("record") == access.get("files") == "public":
        return "open"
    return "restricted"


def _available_date(dates: list[dict[str, Any]]) -> date | None:
    """Return the "Available" date of the dataset (an RDM date, EDTF - the start of an interval)."""
    for rdm_date in dates:
        if (rdm_date.get("type") or {}).get("id") == "available" and rdm_date.get("date"):
            try:
                return date.fromisoformat(rdm_date["date"].split("/")[0][:10])
            except ValueError:
                return None  # a year or a month only - not a day the embargo could end
    return None

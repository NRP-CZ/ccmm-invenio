#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Scan datasets record JSON for ``{"id": ...}`` references.

Run from within the invenio shell::

    invenio shell scripts/migration_vocabs.py

For every dict in the ``json`` column of ``datasets_metadata`` and
``datasets_draft_metadata`` that contains an ``id`` key, prints the path
leading to it (array indices excluded) followed by the id value, e.g.::

    metadata/creators/affiliations/id ror:xxxx
"""

# a migration script run through `invenio shell`: not a package (INP001)
# and reporting through prints (T201)
# ruff: noqa: INP001, T201

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from importlib.resources import files
from os.path import commonprefix
from typing import TYPE_CHECKING, Any

import yaml
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_pidstore.errors import PersistentIdentifierError, PIDAlreadyExists
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.proxies import current_service
from invenio_vocabularies.records.models import VocabularyScheme, VocabularyType
from sqlalchemy import text
from tqdm import tqdm

if TYPE_CHECKING:
    from collections.abc import Iterator
    from importlib.resources.abc import Traversable

    from invenio_records_resources.services import RecordService

TABLES: tuple[str, ...] = ("datasets_metadata", "datasets_draft_metadata")


def find_ids(node: Any, path: str = "") -> Iterator[tuple[str, Any, dict[str, Any]]]:
    """Yield (path, value, parent) of every ``id`` key found in dicts.

    ``parent`` is the dict holding the ``id`` key, so that the value can
    be modified in place.
    """
    if isinstance(node, dict):
        if "id" in node:
            value = node["id"]
            if not isinstance(value, (dict, list)):
                yield f"{path}/id" if path else "id", value, node
        for key, value in node.items():
            if key == "id":
                continue
            yield from find_ids(value, f"{path}/{key}" if path else key)
    elif isinstance(node, list):
        # array indices are excluded from the path
        for item in node:
            yield from find_ids(item, path)


excluded_paths: list[str] = [
    "metadata/funding/funder/id",
    "metadata/creators/affiliations/id",
    "metadata/contributors/affiliations/id",
    "id",
]


@lru_cache(maxsize=1)
def vocabulary_ids() -> frozenset[str]:
    """Set of ids of all vocabulary records, loaded with a single select."""
    rows = db.session.execute(
        text("""
        SELECT json ->> 'id' FROM vocabularies_metadata
        WHERE NOT (COALESCE(json -> 'tags', '[]'::jsonb) ? 'deprecated')
    """)
    )
    return frozenset(row[0] for row in rows if row[0])


@lru_cache(maxsize=1)
def coar_mappings() -> dict[str, str]:
    """Map COAR resource type identifiers to vocabulary item ids."""
    rows = db.session.execute(
        text("""
        SELECT json ->> 'id', json -> 'mappings'
        FROM vocabularies_metadata
        WHERE json -> 'mappings' IS NOT NULL
    """)
    )
    prefix = "http://purl.org/coar/resource_type/"
    return {
        entry["identifier"]: vocab_id
        for vocab_id, mappings in rows
        for entry in mappings or ()
        if str(entry.get("identifier", "")).startswith(prefix)
    }


@lru_cache(maxsize=1)
def subject_ids() -> frozenset[str]:
    """Set of ids of all subject records, loaded with a single select.

    The subjects are their own kind of vocabulary in invenio - they live in
    their own table and are served by their own service - so they are not
    covered by :func:`vocabulary_ids`.
    """
    rows = db.session.execute(
        text("""
        SELECT json ->> 'id' FROM subject_metadata
    """)
    )
    return frozenset(row[0] for row in rows if row[0])


# old cc license ids that do not follow the <version>-<variant> pattern
old_cc_license_ids = {
    "CC": "cc",
    "CC-1.0": "cc-1.0",
    "CC-2.0": "cc-2.0",
    "CC-2.5": "cc-2.5",
    "CC-3.0": "cc-3.0",
    "CC-4.0": "cc-4.0",
    "CC0-1.0": "cc0-1.0",
}

old_cc_license_re = re.compile(r"(\d(?:-5)?)-(BY(?:-[A-Z]{2})*)")
old_cc_versions = {"1": "1.0", "2": "2.0", "2-5": "2.5", "3": "3.0", "4": "4.0"}

date_range_re = re.compile(r"(?P<base>.+?)(?P<suffix>Start|End)")


def merge_descriptions(start: str, end: str) -> str:
    """Return the common prefix of the two range descriptions, cut to a full sentence.

    The ``...Start``/``...End`` descriptions only differ where they talk
    about the start resp. the end of the range (``"...the start date (of
    the range)..."``), so the common prefix is cut back to the last
    punctuation mark and terminated with a dot.
    """
    prefix = commonprefix([start, end]).rstrip()
    for i in range(len(prefix) - 1, -1, -1):
        char = prefix[i]
        if char.isalnum() or char.isspace():
            continue
        if char == ".":
            return prefix[: i + 1]
        if char in ")]}\"'":
            # keep the closed bracket/quote, terminate after it
            return prefix[: i + 1] + "."
        # any other punctuation is replaced by the terminating dot
        return prefix[:i].rstrip() + "."
    return prefix


def date_type_match(entry: dict) -> re.Match | None:
    """Match ``...Start``/``...End`` date type ids, e.g. ``CreatedStart``."""
    type_ = entry.get("type")
    if not isinstance(type_, dict):
        return None
    type_id = type_.get("id")
    if not isinstance(type_id, str):
        return None
    return date_range_re.fullmatch(type_id)


def convert_dates(dates: list[dict]) -> list[dict] | None:
    """Merge ``...Start``/``...End`` date entries into date ranges.

    A ``CreatedStart`` + ``CreatedEnd`` pair becomes a single ``Created``
    entry with ``date`` set to ``<start>/<end>`` and the description cut
    down to the sentence the two originals share. Entries whose type has
    no ``Start``/``End`` suffix are kept as they are.

    Returns the converted list, or None when there is nothing to convert.
    """
    pairs: dict[str, dict[str, dict]] = {}
    for entry in dates:
        match = date_type_match(entry)
        if match is not None:
            pairs.setdefault(match["base"], {})[match["suffix"].lower()] = entry
    if not pairs:
        return None

    converted = []
    merged: set[str] = set()
    for entry in dates:
        match = date_type_match(entry)
        if match is None:
            converted.append(entry)
            continue
        base, suffix = match["base"], match["suffix"]
        if suffix == "End" and base in merged:
            continue  # already merged into its Start entry
        merged.add(base)
        new_entry = dict(entry, type=dict(entry["type"], id=base))
        other = pairs[base].get("end" if suffix == "Start" else "start")
        if other is None:
            print(
                f"dates: {entry['type']['id']} has no matching "
                f"{'End' if suffix == 'Start' else 'Start'} - "
                f"keeping single date {entry['date']}"
            )
        else:
            first, last = (entry, other) if suffix == "Start" else (other, entry)
            new_entry["date"] = f"{first['date']}/{last['date']}"
            description = merge_descriptions(first.get("description", ""), last.get("description", ""))
            if description:
                new_entry["description"] = description
            else:
                new_entry.pop("description", None)
            print(f"dates: {entry['type']['id']} -> {base} {new_entry['date']}")
        converted.append(new_entry)
    return converted


# the two-letter modifiers a cc license variant can be built from - anything
# else trailing the variant is a country code of a ported version (CZ, US, ...)
cc_modifiers = {"BY", "NC", "ND", "SA"}


def convert_cc_license(value: str) -> str | None:
    """Convert an old cc license id (e.g. ``4-BY``) to the spdx-style one.

    Ported country variants (e.g. the Czech ``3-BY-CZ``) are converted to
    their international counterpart (``cc-by-3.0``) - only the international
    versions are in the vocabulary.
    """
    if value in old_cc_license_ids:
        return old_cc_license_ids[value]
    match = old_cc_license_re.fullmatch(value)
    if match is None:
        return None
    version = old_cc_versions[match.group(1)]
    modifiers = match.group(2).split("-")
    while len(modifiers) > 1 and modifiers[-1] not in cc_modifiers:
        modifiers.pop()
    variant = "-".join(modifiers)
    return f"cc-{variant.lower()}-{version}"


def convert_ford(value: str) -> str | None:
    """Convert a FORD classification code (e.g. ``10511``) to its subject id.

    The subjects are identified by the scheme-prefixed classification code
    (``10511`` -> ``ford:10511``); the prefixed form is used as the id only
    when it resolves to a loaded subject (see :func:`subject_ids`).
    """
    candidate = f"ford:{value}"
    return candidate if candidate in subject_ids() else None


def migrate_dates(record_data: dict) -> bool:
    """Migrate the dates from XStart and XEnd to X.

    Returns True when the record's dates were modified.
    """
    metadata = record_data.get("metadata") or {}
    dates = metadata.get("dates")
    if not dates:
        return False
    converted_dates = convert_dates(dates)
    if converted_dates is None:
        return False
    metadata["dates"] = converted_dates
    return True


def converted_id(value: str, vocabs: frozenset[str]) -> str | None:
    """Return the vocabulary id the given old id converts to, if any.

    Lowercase ids, COAR resource type codes, old cc license ids and plain
    FORD codes are converted; the conversion is only accepted when the
    result is an id of a non-deprecated vocabulary record.
    """
    if value.lower() in vocabs:
        return value.lower()
    if new_id := coar_mappings().get(f"http://purl.org/coar/resource_type/{value}"):
        return new_id
    if (new_id := convert_cc_license(value)) and new_id in vocabs:
        return new_id
    return convert_ford(value)


def migrate_data(modify: bool = False) -> None:
    """Convert the old vocabulary ids of the dataset records.

    The ids the records reference are looked up through :func:`converted_id`;
    with ``modify``, the modified records are written back to their tables.
    """
    vocabs = vocabulary_ids()
    for table in TABLES:
        # the table name comes from the local TABLES constant, not untrusted input
        rows = db.session.execute(text(f"SELECT id, json FROM {table}"))  # noqa: S608
        for record_id, data in rows:
            if not data:
                continue
            modified = migrate_dates(data)
            for path, value, parent in find_ids(data):
                if path in excluded_paths or not isinstance(value, str):
                    continue
                if value in vocabs:
                    print(f"{path} {value} is already ok")
                    continue
                if new_id := converted_id(value, vocabs):
                    print(f"{table}[{record_id}] {path}: {value} -> {new_id}")
                    parent["id"] = new_id
                    modified = True
                    continue
                print(f"cannot convert: {path} {value} in {record_id}")
            if modify and modified:
                db.session.execute(
                    # the table name comes from the local TABLES constant, not untrusted input
                    text(f"UPDATE {table} SET json = CAST(:json AS jsonb) WHERE id = :id"),  # noqa: S608
                    {"json": json.dumps(data), "id": record_id},
                )
                db.session.commit()


if not current_app:
    raise SystemExit(
        "No Flask application context active. Run this script via:\n    invenio shell scripts/migration_vocabs.py"
    )

vocabs_to_clean: list[str] = [
    "creatorsroles",
    "contributorsroles",
    "code:programmingLanguages",
    "accessrights",
    "checksumalgorithms",
    "datetypes",
    "languages",
    "communitytypes",
    "locationrelationtypes",
    "titletypes",
    "filetypes",
    "relationtypes",
    "descriptiontypes",
    "identifierschemes",
    "code:developmentStatus",
    "licenses",
    "resourcetypes",
    "subjectcategories",
    "resourceagentroletypes",
    "removalreasons",
    "subjectschemes",
]


def mark() -> None:
    """Mark all items in the vocabs_to_clean as deprecated."""
    result = db.session.execute(
        text("""
            UPDATE vocabularies_metadata
            SET json = jsonb_set(
                json,
                '{tags}',
                COALESCE(json->'tags', '[]'::jsonb) || '["deprecated"]'::jsonb,
                true
            )
            WHERE json->'type'->>'id' IN :types
              AND NOT (COALESCE(json->'tags', '[]'::jsonb) ? 'deprecated')
        """),
        {"types": tuple(vocabs_to_clean)},
    )
    db.session.commit()
    print(f"Marked {result.rowcount} vocabulary records as deprecated.")


def migrate_fileformats() -> None:
    """Migrate the filetypes -> fileformats vocabulary type."""
    result = db.session.execute(
        text("UPDATE vocabularies_types SET id = 'fileformats' WHERE id = 'filetypes'"),
    )
    print(f"Renamed {result.rowcount} vocabulary type filetypes -> fileformats")

    result = db.session.execute(
        text("""
            UPDATE vocabularies_metadata
            SET json = jsonb_set(json, '{type,id}', '"fileformats"'::jsonb)
            WHERE json #>> '{type,id}' = 'filetypes'
        """),
    )
    print(f"Updated type id of {result.rowcount} vocabulary records filetypes -> fileformats")


def migrate_vocabulary_pid_types() -> None:
    """Migrate the pid types of vocabulary records to the new fixture ones."""
    pid_types_table: dict[str, dict[str, str]] = {
        "contributorsroles": {"from": "v-ct", "to": "cor"},
        "datetypes": {"from": "v-dt", "to": "dat"},
        "languages": {"from": "v-lan", "to": "lng"},
        "licenses": {"from": "v-lic", "to": "lic"},
        "relationtypes": {"from": "v-rel", "to": "rlt"},
        "resourcetypes": {"from": "v-res", "to": "rsrct"},
        "titletypes": {"from": "v-tt", "to": "ttyp"},
    }

    for vocabulary_id, pid_types in pid_types_table.items():
        old_pid_type = pid_types["from"]
        new_pid_type = pid_types["to"]

        result = db.session.execute(
            text("UPDATE vocabularies_types SET pid_type = :new WHERE id = :vid AND pid_type = :old"),
            {"new": new_pid_type, "vid": vocabulary_id, "old": old_pid_type},
        )
        print(f"{vocabulary_id}: pid type of {result.rowcount} type row {old_pid_type} -> {new_pid_type}")

        result = db.session.execute(
            text("""
                UPDATE vocabularies_metadata
                SET json = jsonb_set(
                        jsonb_set(
                            json, '{type,pid_type}',
                            to_jsonb(CAST(:new AS text)), false),
                        '{pid,pid_type}',
                        to_jsonb(CAST(:new AS text)), false)
                WHERE json #>> '{type,id}' = :vid
                  AND json #>> '{type,pid_type}' = :old
            """),
            {"new": new_pid_type, "vid": vocabulary_id, "old": old_pid_type},
        )
        print(f"{vocabulary_id}: pid type of {result.rowcount} records {old_pid_type} -> {new_pid_type}")

        result = db.session.execute(
            text("UPDATE pidstore_pid SET pid_type = :new WHERE pid_type = :old"),
            {"new": new_pid_type, "old": old_pid_type},
        )
        print(f"{vocabulary_id}: pid type of {result.rowcount} pids {old_pid_type} -> {new_pid_type}")


def migrate_vocabulary_types() -> None:
    """Rename the filetypes vocabulary type to fileformats, pid type stays v-ft."""
    migrate_fileformats()
    migrate_vocabulary_pid_types()
    db.session.commit()


def load_scheme_entries(service: RecordService, data_file: Traversable) -> None:
    """Load the entries of a scheme's data file through its service.

    Creates the entries that do not exist yet and updates the existing ones -
    the way the subjects service writer of ``invenio_vocabularies`` does.
    """
    entries = yaml.safe_load(data_file.read_text()) or []
    for entry in tqdm(entries, desc=data_file.name, leave=False):
        try:
            service.create(system_identity, entry)
        except PIDAlreadyExists:
            current = service.read(system_identity, entry["id"]).to_dict()
            service.update(system_identity, entry["id"], dict(current, **entry))


def load_new_vocabularies() -> None:
    """Load the ccmm_invenio fixtures, creating or updating vocabulary items."""
    fixtures = files("ccmm_invenio.fixtures")
    index = yaml.safe_load((fixtures / "vocabularies.yaml").read_text())

    record_cls = current_service.record_cls
    for vocabulary_id, config in tqdm(index.items(), desc="vocabularies"):
        # create the vocabulary type if it does not exist yet
        if db.session.get(VocabularyType, vocabulary_id) is None:
            # the pid type may be held by a differently named type - rename it
            existing = db.session.query(VocabularyType).filter_by(pid_type=config["pid-type"]).one_or_none()
            if existing is not None:
                existing.id = vocabulary_id
                db.session.commit()
            else:
                current_service.create_type(system_identity, vocabulary_id, config["pid-type"])

        # the scheme-bearing vocabularies (the subjects): their schemes are
        # registered in their own table and the entries of each scheme's data
        # file are loaded through the vocabulary's own service
        if "schemes" in config:
            service = current_service_registry.get(vocabulary_id)
            for scheme in config["schemes"]:
                if db.session.get(VocabularyScheme, (scheme["id"], vocabulary_id)) is None:
                    VocabularyScheme.create(
                        id=scheme["id"],
                        parent_id=vocabulary_id,
                        name=scheme.get("name", ""),
                        uri=scheme.get("uri", ""),
                    )
                    db.session.commit()
                load_scheme_entries(service, fixtures / scheme["data-file"])
            continue

        entries = yaml.safe_load((fixtures / config["data-file"]).read_text()) or []
        for entry in tqdm(entries, desc=vocabulary_id, leave=False):
            entry["type"] = vocabulary_id
            pid = (vocabulary_id, entry["id"])
            try:
                record_cls.pid.resolve(pid)
            except PersistentIdentifierError:
                current_service.create(system_identity, entry)
            else:
                current_service.update(system_identity, pid, entry)


if len(sys.argv) == 1:
    raise SystemExit("""

No command specified. Call in the following order:

  * mark
  * migrate_types
  * load
  * migrate_data


        """)

match sys.argv[1]:
    case "mark":
        # 1st step: mark existing vocabularies as deprecated until we decide later
        mark()
    case "migrate_types":
        # 2nd migration step - migrate vocabulary types
        migrate_vocabulary_types()
    case "load":
        load_new_vocabularies()
    case "migrate_data":
        migrate_data(modify="--modify" in sys.argv[2:])
    case _:
        raise SystemExit(f"Unknown command: {sys.argv[1]}")

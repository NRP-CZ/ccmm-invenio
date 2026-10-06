#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests of the vocabularies.yaml index export."""

from __future__ import annotations

import pytest
import yaml

from ccmm_invenio.fixtures.compiler.converter import (
    UNINDEXED_VOCABULARIES,
    VOCABULARY_ALIASES,
    VOCABULARY_PID_TYPES,
    VOCABULARY_SCHEMES,
    export_vocabulary_index,
    vocabulary_builders,
)

# the pid types invenio_rdm_records registers its vocabularies with (its
# fixtures/data/vocabularies.yaml) - ours must not diverge from them
RDM_PID_TYPES = {
    "datetypes": "dat",
    "descriptiontypes": "dty",
    "languages": "lng",
    "licenses": "lic",
    "relationtypes": "rlt",
    "removalreasons": "rem",
    "resourcetypes": "rsrct",
    "titletypes": "ttyp",
}


def test_pid_types_match_invenio_rdm_records():
    """Every vocabulary invenio_rdm_records knows keeps its pid type."""
    known_pid_types = {
        **VOCABULARY_PID_TYPES,
        # the vocabularies loaded under an alias keep the pid type of the
        # alias as well
        **{alias: pid_type for alias, (pid_type, _) in VOCABULARY_ALIASES.items()},
    }
    for name, pid_type in RDM_PID_TYPES.items():
        assert known_pid_types[name] == pid_type

    # the remaining vocabularies are NMA-only and take v- pids, which cannot
    # clash with the invenio_rdm_records ones; the aliases carry the pid
    # types of the names they load the vocabularies under instead
    # the subjects excepted: they are a custom vocabulary type of
    # invenio_vocabularies with their own service, records and pid type
    nma_only = set(VOCABULARY_PID_TYPES) - set(RDM_PID_TYPES) - {"subjects", "subjects_inspire"}
    for name in nma_only:
        assert VOCABULARY_PID_TYPES[name].startswith("v-"), name
    assert VOCABULARY_PID_TYPES["subjects"] == VOCABULARY_PID_TYPES["subjects_inspire"] == "sub"


def test_index_covers_all_vocabularies(tmp_path):
    """The index lists every exported vocabulary and no stale entry."""
    builders = vocabulary_builders()
    assert set(builders) == set(VOCABULARY_PID_TYPES)

    output_path = tmp_path / "vocabularies.yaml"
    export_vocabulary_index(builders, output_path)

    index = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    # the whole index - the indexed vocabularies and their aliases - is
    # sorted by name; the unindexed vocabularies are not carried
    indexed = set(builders) - UNINDEXED_VOCABULARIES
    assert list(index) == sorted(indexed | set(VOCABULARY_ALIASES))
    for name in indexed:
        expected = {
            "pid-type": VOCABULARY_PID_TYPES[name],
            "data-file": f"data/{name}.yaml",
        }
        # the scheme-bearing vocabularies carry their schemes as well
        if name in VOCABULARY_SCHEMES:
            expected["schemes"] = [{"data-file": f"data/{name}.yaml", **scheme} for scheme in VOCABULARY_SCHEMES[name]]
        assert index[name] == expected
    for name in UNINDEXED_VOCABULARIES:
        assert name not in index

    # invenio_rdm_records loads resourceagentroletypes.yaml twice, under its
    # own pid types
    assert index["creatorsroles"] == {"pid-type": "crr", "data-file": "data/resourceagentroletypes.yaml"}
    assert index["contributorsroles"] == {"pid-type": "cor", "data-file": "data/resourceagentroletypes.yaml"}

    # the used languages are the primary ones, not the full ISO 639-3
    # vocabulary
    assert index["languages"] == {"pid-type": "lng", "data-file": "data/languages_primary.yaml"}

    # the subjects are their own kind of vocabulary in invenio: their index
    # entry carries their schemes, registered by the fixture loader in its
    # own table and loading the subjects data file through the subjects
    # service
    assert index["subjects"] == {
        "pid-type": "sub",
        "data-file": "data/subjects.yaml",
        "schemes": [
            {
                "id": "FORD",
                "name": "OECD FORD Subject Category (Frascati)",
                "uri": "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/",
                "data-file": "data/subjects.yaml",
            },
            # the INSPIRE themes are in their own data file
            {
                "id": "INSPIRE",
                "name": "INSPIRE theme register",
                "uri": "http://inspire.ec.europa.eu/theme",
                "data-file": "data/subjects_inspire.yaml",
            },
        ],
    }


def test_index_rejects_stale_aliases(tmp_path):
    """An alias of a vocabulary that is not exported fails the export."""
    builders = vocabulary_builders()
    builders.pop("resourceagentroletypes")

    with pytest.raises(KeyError, match="stale aliases"):
        export_vocabulary_index(builders, tmp_path / "vocabularies.yaml")


def test_index_rejects_stale_unindexed(tmp_path):
    """An unindexed vocabulary that is not exported fails the export."""
    builders = vocabulary_builders()
    builders.pop("languages_all")

    with pytest.raises(KeyError, match="stale unindexed"):
        export_vocabulary_index(builders, tmp_path / "vocabularies.yaml")


def test_index_rejects_stale_schemes(tmp_path):
    """A scheme-bearing vocabulary that is not exported fails the export."""
    builders = vocabulary_builders()
    builders.pop("subjects")

    with pytest.raises(KeyError, match="stale schemes"):
        export_vocabulary_index(builders, tmp_path / "vocabularies.yaml")


def test_index_rejects_stale_pid_types(tmp_path):
    """A pid type without a vocabulary fails the export, not silently."""
    with pytest.raises(KeyError, match="stale pids"):
        export_vocabulary_index({}, tmp_path / "vocabularies.yaml")


def test_index_rejects_missing_pid_types(tmp_path):
    """A vocabulary without a pid type fails the export, not silently."""
    builders = {"languages_primary": vocabulary_builders()["languages_primary"]}
    builders["notavocabulary"] = builders["languages_primary"]

    with pytest.raises(KeyError, match="missing pids"):
        export_vocabulary_index(builders, tmp_path / "vocabularies.yaml")

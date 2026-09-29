#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Convert the vocabulary sources into Invenio vocabulary fixtures."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml
from rdflib import Graph, Literal, URIRef
from tqdm import tqdm

from .invenio_export import enclosing_namespace, export_subjects, export_vocabulary
from .merger import MappingsMerger
from .prefixes import TURTLE_PREFIXES
from .readers import (
    INSPIRE_SCHEME,
    SUBJECT_SCHEME,
    CCMMDateTypesReader,
    CCMMDescriptionTypesReader,
    CCMMLocationRelationsReader,
    CCMMRelationTypeReader,
    CCMMRolesReader,
    CCMMTitleTypesReader,
    COARAccessRightsReader,
    COARResourceTypesReader,
    CuratedVocabularyReader,
    DataciteReader,
    DataciteRelationTypeReader,
    DateTypesMerger,
    DescriptionTypesMerger,
    EUFileFormatsReader,
    IANAMediaTypesReader,
    IdentifiersMerger,
    InspireThemesReader,
    LanguageReader,
    LicensesMerger,
    OverlayReader,
    PrimaryLanguagesReader,
    RDMDateTypesReader,
    RDMDescriptionTypesReader,
    RDMIdentifierSchemesReader,
    RDMLicensesReader,
    RDMRemovalReasonsReader,
    RDMResourceTypesReader,
    RDMRolesReader,
    RDMTitleTypesReader,
    RelationTypesMerger,
    ResourceTypesMerger,
    RolesMerger,
    SPDXChecksumAlgorithmsReader,
    SSSOMMappingsReader,
    SubjectsReader,
    TitleTypesMerger,
    VocabularyReader,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from .merger import VocabularyMerger

DATA_DIR = Path(str(files("ccmm_invenio.fixtures.input.vocabularies")))
"""Directory of the locally curated data: SSSOM mapping sets, prop
overlays and curated concept fragments."""


@lru_cache(maxsize=1)
def datacite_distribution() -> Graph:
    """Read the TIB DataCite distribution, shared by its vocabulary readers.

    The distribution integrates all DataCite vocabularies in one document;
    it is fetched once, however many of its vocabularies are read.
    """
    return DataciteReader().read()


@lru_cache(maxsize=1)
def languages_distribution() -> Graph:
    """Read the ISO 639-3 languages, shared by its vocabulary readers.

    The full languages vocabulary and its primary subset are built from the
    same pycountry data; the graph is built once, however many of its
    vocabularies are read.
    """
    return LanguageReader().read()


def used_namespaces(graph: Graph) -> set[str]:
    """Collect the namespaces of all the URIs of a graph.

    The namespace of a term is its enclosing namespace (see
    :func:`enclosing_namespace`); the datatypes of typed literals count as
    their terms - a notation is identified by the URI of its scheme.
    """
    namespaces = set()
    for subject, predicate, value in graph:
        for term in (subject, predicate, value):
            if isinstance(term, URIRef):
                namespaces.add(enclosing_namespace(str(term)))
            elif isinstance(term, Literal) and term.datatype:
                namespaces.add(enclosing_namespace(str(term.datatype)))
    return namespaces


def export_turtle(graph: Graph, output_path: Path) -> None:
    """Serialize a vocabulary graph as turtle, deterministically.

    rdflib invents the ``ns1``, ``ns2``, ... prefixes of unbound namespaces
    in the order it happens to encounter them - which varies with the hash
    seed of the run, changing lines all over the output. The namespaces of
    the graph are therefore bound here: the well-known ones to their
    prefixes (:data:`TURTLE_PREFIXES`), the remaining ones to ``ns1``,
    ``ns2``, ... by their sorted position. The rest of the serializer
    output is ordered (subjects, predicates, objects, prefixes), so the
    files stay put when the vocabularies change.
    """
    for prefix, namespace in TURTLE_PREFIXES.items():
        graph.bind(prefix, namespace)

    bound = {str(namespace) for _, namespace in graph.namespaces()}
    unbound = used_namespaces(graph) - bound
    for number, namespace in enumerate(sorted(unbound), start=1):
        graph.bind(f"ns{number}", namespace)

    graph.serialize(destination=output_path, format="turtle")


def overlay(graph: Graph, *overlays: VocabularyReader) -> Graph:
    """Merge overlays into a built vocabulary graph.

    The overlays (e.g. :class:`~.readers.overlay.OverlayReader` instances
    of our curated props, or :class:`~.readers.sssom.SSSOMMappingsReader`
    mapping sets) are read after the graph is built and merged into it with
    :class:`~.merger.MappingsMerger` - strictly, so a prop or mapping of a
    concept the vocabulary does not know fails the conversion instead of
    being silently dropped.

    Args:
        graph: the vocabulary graph the overlays are merged into
        overlays: the readers of the overlay graphs to merge in

    """
    for overlay_reader in overlays:
        MappingsMerger(overlay_reader.read(), graph).merge()
    return graph


def with_overlay(name: str, build: Callable[[], Graph]) -> Callable[[], Graph]:
    """Wrap a builder with the curated overlay of the given vocabulary name.

    The overlay is the turtle file the vocabulary's props and tags are
    curated in (``{name}.ttl`` of :data:`DATA_DIR`, read by
    :class:`~.readers.overlay.OverlayReader`); see :func:`overlay` for how
    it is merged in.
    """
    return lambda: overlay(build(), OverlayReader(DATA_DIR / f"{name}.ttl"))


def merged(
    source: VocabularyReader,
    target: VocabularyReader,
    merger: Callable[[Graph, Graph], VocabularyMerger],
) -> Callable[[], Graph]:
    """Return a builder that reads a target vocabulary and merges its source into it.

    The target is read first and merged into, so that its structure (the
    Invenio ids, the scheme, the tags) is the backbone the source concepts
    enrich. The source concepts without a target counterpart are pulled in
    as well - they are exactly the ones a conversion from CCMM records
    needs but Invenio does not know yet. Building the readers is cheap, so
    the deferring is all in the ``read()`` calls, run when the returned
    builder is called.
    """

    def build() -> Graph:
        graph = target.read()
        merger(source.read(), graph).merge(add_missing=True)
        return graph

    return build


VOCABULARY_PID_TYPES = {
    # pid types of invenio_rdm_records - kept identical (its
    # fixtures/data/vocabularies.yaml), so that its vocabularies are not
    # registered twice with different pids when both indexes are loaded
    "datetypes": "dat",
    "descriptiontypes": "dty",
    "licenses": "lic",
    "relationtypes": "rlt",
    "removalreasons": "rem",
    "resourcetypes": "rsrct",
    "titletypes": "ttyp",
    # the NMA-only vocabularies take v- pids, which cannot clash with the
    # invenio_rdm_records ones; the pids of the old index are kept (v-ar of
    # accessrights, v-ft of fileformats - filetypes back then, v-lr of
    # locationrelations, v-agr of resourceagentroletypes)
    "accessrights": "v-ar",
    "checksumalgorithms": "v-ca",
    "fileformats": "v-ft",
    "identifierschemes": "v-ids",
    "languages_all": "v-lan",
    "languages_primary": "v-lp",
    "locationrelations": "v-lr",
    "mediatypes": "v-mt",
    "resourceagentroletypes": "v-agr",
    # subjects are their own kind of vocabulary in invenio - a custom
    # vocabulary type with its own service and pid type
    "subjects": "sub",
    # the INSPIRE themes - a second scheme of the subjects, loaded from its own data file
    "subjects_inspire": "sub",
}
"""The pid types of the exported vocabularies, by their names."""

VOCABULARY_ALIASES = {
    # invenio_rdm_records loads its roles fixture (resourceagentroletypes in
    # ccmm, pid v-agr) twice, as creatorsroles (crr, the roles of creators)
    # and contributorsroles (cor, the roles of contributors); the index
    # carries both aliases of the resourceagentroletypes vocabulary with the
    # pid types of invenio_rdm_records, so that the components that look the
    # roles up under those names find them.
    "creatorsroles": ("crr", "resourceagentroletypes"),
    "contributorsroles": ("cor", "resourceagentroletypes"),
    # the used languages are the primary ones: the languages vocabulary
    # (lng, the pid type of invenio_rdm_records) loads the primary subset,
    # the full ISO 639-3 vocabulary is exported for reference only
    "languages": ("lng", "languages_primary"),
}
"""The extra index entries of vocabularies known under several names.

Maps the alias name to the pid type it is registered with and to the
vocabulary (a :func:`vocabulary_builders` name) whose data file it loads.
"""

UNINDEXED_VOCABULARIES = {
    # exported into their own fixture files but not carried in the index:
    # the primary languages are loaded under the languages alias (see
    # :data:`VOCABULARY_ALIASES`) and the full ISO 639-3 languages are not
    # used at all and kept for reference only
    "languages_all",
    "languages_primary",
    # loaded as the INSPIRE scheme of the subjects (see VOCABULARY_SCHEMES)
    "subjects_inspire",
}
"""The exported vocabularies the vocabularies.yaml index does not list."""

VOCABULARY_SCHEMES = {
    # subjects are a custom vocabulary type in invenio - the fixture loader
    # registers each of their schemes (its id, name and uri) in its own
    # vocabularies_schemes table and loads the data file of the scheme
    # through the subjects service, not the vocabularies one
    "subjects": [
        {
            "id": SUBJECT_SCHEME,
            "name": "OECD FORD Subject Category (Frascati)",
            "uri": "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/",
        },
        {
            "id": INSPIRE_SCHEME,
            "name": "INSPIRE theme register",
            "uri": "http://inspire.ec.europa.eu/theme",
            "data-file": "data/subjects_inspire.yaml",
        },
    ],
}
"""The schemes of the scheme-bearing vocabularies (the subjects), by their names.

Each scheme loads the vocabulary's own data file, unless it names its own "data-file"
(a vocabulary of :data:`UNINDEXED_VOCABULARIES`)."""

SUBJECT_SCHEMES = {
    "subjects": SUBJECT_SCHEME,
    "subjects_inspire": INSPIRE_SCHEME,
}
"""The subjects vocabularies (exported as subjects fixtures), by their names, with the scheme of their entries."""


def vocabulary_builders() -> dict[str, Callable[[], Graph]]:
    """Collect the builders of the vocabulary graphs of all sources.

    Returns a mapping of the vocabulary types (the fixture filenames) to
    zero-argument builders, so that the caller decides when each source is
    read (and fetched). The vocabularies with a CCMM codelist source are
    built by merging that source into their Invenio counterpart.
    """
    return {
        "accessrights": with_overlay("accessrights", COARAccessRightsReader().read),
        "checksumalgorithms": SPDXChecksumAlgorithmsReader().read,
        "datetypes": with_overlay(
            "datetypes",
            merged(CCMMDateTypesReader(), RDMDateTypesReader(), DateTypesMerger),
        ),
        "descriptiontypes": merged(
            CCMMDescriptionTypesReader(),
            RDMDescriptionTypesReader(),
            DescriptionTypesMerger,
        ),
        "fileformats": EUFileFormatsReader().read,
        "identifierschemes": merged(
            CuratedVocabularyReader(DATA_DIR / "identifierschemes.ttl", "identifierschemes"),
            RDMIdentifierSchemesReader(),
            IdentifiersMerger,
        ),
        "languages_all": languages_distribution,
        "languages_primary": PrimaryLanguagesReader(languages_distribution).read,
        "licenses": merged(
            CuratedVocabularyReader(DATA_DIR / "licenses.ttl", "licenses"),
            RDMLicensesReader(),
            LicensesMerger,
        ),
        "locationrelations": CCMMLocationRelationsReader().read,
        "mediatypes": IANAMediaTypesReader().read,
        "relationtypes": with_overlay(
            "relationtypes",
            merged(
                CCMMRelationTypeReader(),
                DataciteRelationTypeReader(datacite_distribution),
                RelationTypesMerger,
            ),
        ),
        "removalreasons": RDMRemovalReasonsReader().read,
        "resourcetypes": with_overlay(
            "resourcetypes",
            lambda: ResourceTypesMerger(
                COARResourceTypesReader().read(),
                overlay(
                    RDMResourceTypesReader().read(),
                    SSSOMMappingsReader(DATA_DIR / "resource_types.yaml"),
                ),
            ).merge(add_missing=True),
        ),
        "resourceagentroletypes": with_overlay(
            "roles",
            merged(CCMMRolesReader(), RDMRolesReader(), RolesMerger),
        ),
        "subjects": SubjectsReader().read,
        "subjects_inspire": InspireThemesReader().read,
        "titletypes": with_overlay(
            "titletypes",
            merged(CCMMTitleTypesReader(), RDMTitleTypesReader(), TitleTypesMerger),
        ),
    }


def export_vocabulary_index(builders: dict[str, Callable[[], Graph]], output_path: Path) -> None:
    """Write the ``vocabularies.yaml`` index of the exported fixtures.

    The index maps each vocabulary name to its pid type
    (:data:`VOCABULARY_PID_TYPES`) and to the fixture file the converter has
    written for it; the vocabularies known under several names are carried
    under each of them (:data:`VOCABULARY_ALIASES`), e.g.
    resourceagentroletypes both as itself and as the creatorsroles and
    contributorsroles of invenio_rdm_records. The vocabularies of
    :data:`UNINDEXED_VOCABULARIES` are not listed - they are exported for
    reference or loaded under another name.
    The scheme-bearing vocabularies (:data:`VOCABULARY_SCHEMES`, the
    subjects) carry their schemes instead: each scheme loads the
    vocabulary's own data file through its own service (the subjects one),
    so the loader needs the schemes registered in the index.
    The keys must cover exactly the vocabularies :func:`vocabulary_builders`
    builds - a vocabulary without an entry (or an entry without a vocabulary)
    is a bug and fails the export instead of silently dropping the vocabulary
    from the index. The entries are written in the sorted order of their
    names for reproducible outputs.

    Args:
        builders: the vocabulary builders of :func:`vocabulary_builders`
        output_path: path of the vocabularies.yaml file to write

    """
    missing = set(builders) - set(VOCABULARY_PID_TYPES)
    stale = set(VOCABULARY_PID_TYPES) - set(builders)
    stale_aliases = {alias: name for alias, (_, name) in VOCABULARY_ALIASES.items() if name not in builders}
    stale_unindexed = UNINDEXED_VOCABULARIES - set(builders)
    stale_schemes = set(VOCABULARY_SCHEMES) - set(builders)
    if missing or stale or stale_aliases or stale_unindexed or stale_schemes:
        raise KeyError(
            f"the vocabulary index does not match the exported vocabularies "
            f"(missing pids: {sorted(missing)}, stale pids: {sorted(stale)}, "
            f"stale aliases: {sorted(stale_aliases)}, "
            f"stale unindexed: {sorted(stale_unindexed)}, "
            f"stale schemes: {sorted(stale_schemes)})"
        )

    index = {}
    for name in builders:
        if name in UNINDEXED_VOCABULARIES:
            continue
        entry: dict[str, Any] = {
            "pid-type": VOCABULARY_PID_TYPES[name],
            "data-file": f"data/{name}.yaml",
        }
        if name in VOCABULARY_SCHEMES:
            entry["schemes"] = [{"data-file": f"data/{name}.yaml", **scheme} for scheme in VOCABULARY_SCHEMES[name]]
        index[name] = entry
    for alias, (pid_type, name) in VOCABULARY_ALIASES.items():
        index[alias] = {
            "pid-type": pid_type,
            "data-file": f"data/{name}.yaml",
        }
    index = dict(sorted(index.items()))
    with Path(output_path).open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(
            index,
            output_file,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


@click.command()
@click.argument(
    "output_directory",
    type=click.Path(file_okay=False, path_type=Path),
    default="fixtures",
)
def main(output_directory: Path) -> None:
    """Convert the vocabulary sources into Invenio fixtures.

    Reads every vocabulary from its source (the InvenioRDM fixtures, the
    CCMM codelists, the DataCite, COAR, EU, IANA, ... registries), merges
    the CCMM concepts into their Invenio counterparts and exports each
    vocabulary twice into OUTPUT_DIRECTORY/data (created when missing): as
    an Invenio YAML fixture and as the turtle serialization of its graph,
    which keeps what the fixtures cannot express (the scheme structure, the
    exact matches, ...). The vocabularies.yaml index of the exported
    fixtures is written into OUTPUT_DIRECTORY itself - where the RDM
    extension fixture loader (PrioritizedVocabulariesFixtures, the
    invenio_rdm_records.fixtures entry points) looks for it, resolving the
    data files relative to it.
    """
    data_directory = output_directory / "data"
    data_directory.mkdir(parents=True, exist_ok=True)

    builders = vocabulary_builders()
    for name, build in tqdm(builders.items(), unit="vocab", desc="vocabularies"):
        graph = build()
        if name in SUBJECT_SCHEMES:
            # subjects are their own kind of vocabulary in invenio (a custom
            # vocabulary type with its own service, records and schema), so
            # they are exported as a subjects fixture instead of the
            # vocabulary one, each scheme into its own file
            export_subjects(graph, data_directory / f"{name}.yaml", SUBJECT_SCHEMES[name])
        else:
            export_vocabulary(graph, data_directory / f"{name}.yaml")
        export_turtle(graph, data_directory / f"{name}.ttl")

    export_vocabulary_index(builders, output_directory / "vocabularies.yaml")


if __name__ == "__main__":
    main()

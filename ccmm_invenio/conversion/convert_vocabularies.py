import traceback
from functools import partial
from pathlib import Path

import click
import yaml
from tqdm import tqdm

from ccmm_invenio.conversion.base import VocabularyReader
from ccmm_invenio.conversion.ccmm_copy import CopyReader  # noqa
from ccmm_invenio.conversion.ccmm_csv import CSVReader  # noqa
from ccmm_invenio.conversion.ccmm_filtered import (  # noqa
    DescendantsOfFilter,
    FilteredReader,
)
from ccmm_invenio.conversion.ccmm_sparql import SPARQLReader  # noqa


@click.command()
@click.argument("vocabulary_names", nargs=-1)
def convert_vocabularies(vocabulary_names: list[str]) -> None:
    root_dir = Path(__file__).parent.parent

    converters: list[tuple[VocabularyReader, Path]] = [
        (
            # TODO: the CSV does not include dataCiteCode, we needd to add it there !!!
            CSVReader("Agent Role", root_dir / "input/CCMM_slovniky(AgentRole).csv"),
            root_dir / "fixtures/ccmm_agent_roles.yaml",
        ),
        (
            CSVReader(
                "Alternate Title",
                root_dir / "input/CCMM_slovniky(AlternateTitle).csv",
            ),
            root_dir / "fixtures/ccmm_alternate_title_types.yaml",
        ),
        (
            CSVReader(
                "Location Relation",
                root_dir / "input/CCMM_slovniky(LocationRelation).csv",
            ),
            root_dir / "fixtures/ccmm_location_relation_types.yaml",
        ),
        (
            CSVReader(
                "Relation Type",
                root_dir / "input/CCMM_slovniky(RelationType).csv",
                extra=[root_dir / "input/addon_relation_types.csv"],
            ),
            root_dir / "fixtures/ccmm_relation_types.yaml",
        ),
        (
            CSVReader(
                "Subject Category",
                root_dir / "input/CCMM_slovniky(SubjectCategory).csv",
            ),
            root_dir / "fixtures/ccmm_subject_categories.yaml",
        ),
        (
            CSVReader(
                "Time Reference",
                root_dir / "input/CCMM_slovniky(TimeReference).csv",
            ),
            root_dir / "fixtures/ccmm_time_reference_types.yaml",
        ),
        (
            SPARQLReader(
                "Languages",
                "http://publications.europa.eu/resource/authority/language",
                "http://publications.europa.eu/resource/authority/language",
                extra_props={
                    "ISO_639_2T": """
                        ?concept skos:notation ?ISO_639_2T FILTER(datatype(?ISO_639_2T) = euvoc:ISO_639_2T)
                    """,
                    "ISO_639_1": """
                        ?concept skos:notation ?ISO_639_1 FILTER(datatype(?ISO_639_1) = euvoc:ISO_639_1)
                    """,
                    "ISO_639_3": """
                        ?concept skos:notation ?ISO_639_3 FILTER(datatype(?ISO_639_3) = euvoc:ISO_639_3)
                    """,
                    "XML_LNG": """
                        ?concept skos:notation ?XML_LNG FILTER(datatype(?XML_LNG) = euvoc:XML_LNG)
                    """,
                    "ISO_639_2B": """
                        ?concept skos:notation ?ISO_639_2B FILTER(datatype(?ISO_639_2B) = euvoc:ISO_639_2B)
                    """,
                },
                prefixes={
                    "euvoc": "http://publications.europa.eu/ontology/euvoc#",
                },
            ),
            root_dir / "fixtures/ccmm_languages.yaml",
        ),
        (
            SPARQLReader(
                "Access Rights",
                "https://vocabularies.coar-repositories.org/access_rights/access_rights.nt",
                "http://purl.org/coar/access_right/scheme",
                format="turtle",
                load_subgraphs=False,
                extra=root_dir / "input/addon_access_rights.ttl",
            ),
            root_dir / "fixtures/ccmm_access_rights.yaml",
        ),
        (
            SPARQLReader(
                "Resource Type",
                "https://vocabularies.coar-repositories.org/resource_types/resource_types.nt",
                "http://purl.org/coar/resource_type/scheme",
                format="turtle",
                load_subgraphs=False,
                extra=root_dir / "input/addon_resource_types.ttl",
                extra_props={
                    "zenodo": """
                        ?concept props:zenodo ?zenodo
                    """,
                },
                prefixes={
                    "props": "http://vocabs.ccmm.cz/props/",
                },
                array_resolution=zenodo_resource_type_array_resolution,
            ),
            root_dir / "fixtures/ccmm_resource_types.yaml",
        ),
        (
            SPARQLReader(
                "File types",
                "http://publications.europa.eu/resource/authority/file-type",
                "http://publications.europa.eu/resource/authority/file-type",
            ),
            root_dir / "fixtures/ccmm_file_types.yaml",
        ),
        (
            CopyReader(
                "Licenses",
                root_dir / "input/licenses.yaml",
            ),
            root_dir / "fixtures/ccmm_licenses.yaml",
        ),
        (
            CopyReader(
                "Subject schemes",
                root_dir / "input/subject_schemes.yaml",
            ),
            root_dir / "fixtures/ccmm_subject_schemes.yaml",
        ),
        (
            FilteredReader(
                "Contributor type",
                root_dir / "fixtures/ccmm_agent_role.yaml",
                filter_cls=partial(
                    DescendantsOfFilter,
                    descendants_of={
                        "https://vocabs.ccmm.cz/registry/codelist/AgentRole/Contributor"
                    },
                ),
            ),
            root_dir / "fixtures/ccmm_contributor_types.yaml",
        ),
    ]

    if not vocabulary_names:
        vocabulary_names = [reader.name for reader, _ in converters]

    with_progress = tqdm(converters, leave=False, unit="vocab")
    for reader, output_path in with_progress:
        if reader.name not in vocabulary_names:
            continue
        try:
            with_progress.set_description(reader.name)
            with_progress.refresh()
            data = reader.data()
            with open(output_path, "w", encoding="utf-8") as output_file:
                yaml.safe_dump_all(
                    data,
                    output_file,
                    allow_unicode=True,
                    default_flow_style=False,
                )
        except Exception as e:
            print(f"Error converting {reader.name}: {e}")
            traceback.print_exc()


def zenodo_resource_type_array_resolution(prop: str, parent: dict[str, str]) -> None:
    values = parent[prop]
    parent[prop] = ", ".join(sorted(values))

    if prop == "zenodo":
        for value in values:
            parent[f"zenodo-{value}"] = "true"


if __name__ == "__main__":
    convert_vocabularies()

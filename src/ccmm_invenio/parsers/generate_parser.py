#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Generate a parser of CCMM XML.

This script generates parser functions for each complex type defined
in the CCMM model that is passed as an argument to the script. The generated
parser functions are written to the specified output file.

You need to wrap the generated functions in a class that inherits from CCMMXMLParser.
"""

from pathlib import Path
from textwrap import indent

import click
import yaml


@click.command()
@click.argument("ccmm_yaml", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument(
    "ccmm_vocabularies_yaml",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.argument("gml_yaml", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument("output_parser_file", type=click.Path())
def generate_parser(ccmm_yaml: str, ccmm_vocabularies_yaml: str, gml_yaml: str, output_parser_file: str) -> None:
    """Create an overview of the schema types in the given directory."""
    ccmm_model, ccmm_vocabularies = load_models(ccmm_yaml, ccmm_vocabularies_yaml, gml_yaml)

    known_vocabularies = {
        vocab_type_name: vocab_definition["vocabulary-type"]
        for vocab_type_name, vocab_definition in ccmm_vocabularies.items()
    }
    click.secho("Known vocabularies:", fg="green")
    for vocab in known_vocabularies:
        click.secho(f"  - {vocab}", fg="green")

    ret: list[str] = []
    for type_name, type_definition in ccmm_model.items():
        if type_definition.get("parser", {}).get("generate", True) is False:
            click.secho(f"Skipping type without parser: {type_name}", fg="yellow")
            continue

        generate_type_definition(type_name, type_definition, ccmm_model, known_vocabularies, ret)

    with Path(output_parser_file).open("w", encoding="utf-8") as f:
        f.write(class_beginning)
        f.write(indent("\n".join(ret), "    "))


def generate_type_definition(
    type_name: str,
    type_definition: dict,
    ccmm_model: dict,
    known_vocabularies: dict,
    ret: list[str],
) -> None:
    """Generate parser function for a given type definition."""
    click.secho(f"Generating parser for type: {type_name}", fg="green")
    type_ = type_definition.get("type")
    xml_type_name = type_definition.get("xml", type_name)

    if type_ == "array":
        type_definition = type_definition["items"]

    if "properties" not in type_definition:
        click.secho(f"Skipping non-complex type: {type_name}", fg="yellow")
        return  # Skip non-complex types

    fields = type_definition["properties"]

    ret.append("@datatype_parser()")
    ret.append(f"def parse_{type_name.lower()}(self, el: Element, path: list[QualifiedTag]) -> dict:")
    ret.append(f'    """Parse an element of type {xml_type_name} to {type_name}."""')
    ret.append("    children = self.children(el)")
    ret.append("    return {")
    for field_name, field_definition in fields.items():
        field_type = field_definition.get("type")
        is_array = is_field_array(field_definition, ccmm_model)
        required = field_definition.get("required", False)
        xml_field_name = field_definition.get("xml", field_name)
        if field_type == "array":
            field_definition = field_definition["items"]  # noqa: PLW2901
            field_type = field_definition.get("type")

        click.secho(
            f"  Field: {field_name} [{field_type}] [vocabulary={field_type in known_vocabularies}]",
            fg="blue",
        )
        if ":" in xml_field_name:
            namespaced_field = "self." + xml_field_name.replace(":", ".")
        else:
            namespaced_field = f"self.ns.{xml_field_name}"

        if field_type == "multilingual":
            ret.append(
                f"""
    "{field_name}": self.parse_multilingual(
        {namespaced_field},
        children,
        path,
        cardinality="{get_cardinality(required, is_array)}",
    ),"""
            )
        elif field_type == "i18n":
            ret.append(
                f"""
    "{field_name}": self.parse_i18n(
        {namespaced_field},
        children,
        path,
        cardinality="{get_cardinality(required, is_array)}",
    ),"""
            )
        elif field_type in ("keyword", "fulltext", "fulltext+keyword"):
            ret.append(
                f"""
    "{field_name}": self.parse_text_field(
        {namespaced_field},
        children,
        path,
        cardinality="{get_cardinality(required, is_array)}",
    ),"""
            )
        elif field_type in known_vocabularies:
            vocabulary_parser = f"{known_vocabularies[field_type]}_parser"
            ret.append(
                f"""
    "{field_name}": self.{vocabulary_parser}.parse_field(
        {namespaced_field},
        children,
        path,
        cardinality="{get_cardinality(required, is_array)}",
    ),"""
            )
        else:
            ret.append(
                f"""
    "{field_name}": self.parse_field(
        {namespaced_field},
        children,
        path,
        cardinality="{get_cardinality(required, is_array)}",
        datatype="{field_type.lower()}",
    ),"""
            )

    ret.append("    }")


def load_models(ccmm_yaml: str, ccmm_vocabularies_yaml: str, gml_yaml: str) -> tuple[dict, dict]:
    """Load and merge CCMM and GML models from YAML files."""
    with Path(ccmm_yaml).open("r", encoding="utf-8") as f:
        ccmm_model = yaml.safe_load(f)
    with Path(ccmm_vocabularies_yaml).open("r", encoding="utf-8") as f:
        ccmm_vocabularies = yaml.safe_load(f)
    with Path(gml_yaml).open("r", encoding="utf-8") as f:
        gml_model = yaml.safe_load(f)

    ccmm_model.update(gml_model)
    return ccmm_model, ccmm_vocabularies


def get_cardinality(required: bool, array: bool) -> str:
    """Get cardinality string based on required and array flags."""
    if required and array:
        return "array"
    if required and not array:
        return "single"
    if not required and array:
        return "optional_array"
    return "optional"


def is_field_array(field_definition: dict, ccmm_model: dict) -> bool:
    """Determine if a field is an array based on its definition."""
    field_type = field_definition.get("type")
    if field_type == "array":
        return True
    if field_type in ccmm_model:
        type_def = ccmm_model[field_type]
        if type_def.get("type") == "array":
            return True
    return False


class_beginning = '''
#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Parser for CCMM XML version 1.1.0 for NMA."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from .base import CCMMXMLParser, QualifiedTag, VocabularyLoader, XMLNamespace, datatype_parser

if TYPE_CHECKING:
    from lxml.etree import _Element as Element

class CCMMXMLNMAParser(CCMMXMLParser):
    """Parser for CCMM XML version 1.1.0 for NMA."""

    # ccmm namespace
    ns = XMLNamespace("https://schema.ccmm.cz/research-data/1.0")
    gml = XMLNamespace("http://www.opengis.net/gml/3.2")

    def __init__(self, vocabulary_loader: VocabularyLoader):
        """Initialize the parser with the given vocabulary loader."""
        super().__init__(vocabulary_loader)

        self.titletypes_parser = self.register_vocabulary_parser("titletypes")
        self.descriptiontypes_parser = self.register_vocabulary_parser(
            "descriptiontypes"
        )
        self.identifierschemes_parser = self.register_vocabulary_parser(
            "identifierschemes"
        )
        self.languages_parser = self.register_vocabulary_parser("languages")
        self.resourcetypes_parser = self.register_vocabulary_parser("resourcetypes")
        self.datetypes_parser = self.register_vocabulary_parser("datetypes")
        self.accessrights_parser = self.register_vocabulary_parser("accessrights")
        self.license_parser = self.register_vocabulary_parser("licenses")
        self.resourcerelationtypes_parser = self.register_vocabulary_parser(
            "resourcerelationtypes"
        )
        self.checksumalgorithms_parser = self.register_vocabulary_parser(
            "checksumalgorithms"
        )
        self.fileformats_parser = self.register_vocabulary_parser("fileformats")
        self.mediatypes_parser = self.register_vocabulary_parser("mediatypes")
        self.locationrelationtypes_parser = self.register_vocabulary_parser(
            "locationrelationtypes"
        )
        self.resourceagentroletypes_parser = self.register_vocabulary_parser(
            "resourceagentroletypes"
        )
        self.subjectschemes_parser = self.register_vocabulary_parser("subjectschemes")

    @override
    def parse(self, xml_root: Element) -> dict[str, Any]:
        """Parse the root element of the CCMM XML record."""
        record: dict[str, Any] = {}

        record["metadata"] = self.parse_ccmmdataset(xml_root, [])
        return record

'''

if __name__ == "__main__":
    generate_parser()

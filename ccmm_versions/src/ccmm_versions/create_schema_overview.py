"""Create an overview of the schema types in the given directory."""

import dataclasses
from pathlib import Path

import click
from lxml import etree
from lxml.etree import _Element as Element

from ccmm_versions.identify_anonymous_types import is_multilingual


@dataclasses.dataclass
class FieldOverview:
    """Overview information about a field in a type in the schema."""

    name: bool
    type: str
    required: bool
    array: bool


@click.command()
@click.argument("dirname", type=click.Path(exists=True, file_okay=False))
@click.argument("output_markdown_file", type=click.Path())
def create_schema_overview(dirname: str, output_markdown_file: str) -> None:
    """Create an overview of the schema types in the given directory."""
    type_overview = parse_files(dirname)

    with Path(output_markdown_file).open("w", encoding="utf-8") as f:
        f.write("# Schema Overview\n\n")
        for type_name, fields in sorted(type_overview.items()):
            f.write(f"## Type: {type_name}\n\n")
            f.write("| Name | Type | Required | Array |\n")
            f.write("|------|------|----------|-------|\n")

            def is_array(field: FieldOverview) -> bool:
                return field.array and (field.type != "multilingual")

            f.writelines(
                f"| {field.name} | {field.type}"
                f" | {'✔️' if field.required else ''}"
                f" | {'✔️' if is_array(field) else ''} |\n"
                for field in fields
            )
            f.write("\n")


def parse_files(dirname: str) -> dict[str, list[FieldOverview]]:
    """Parse all XSD files in the given directory and return type overview."""
    type_overview: dict[str, list[FieldOverview]] = {}
    for xsd_file in Path(dirname).glob("*.xsd"):
        click.secho(f"Checking: {xsd_file}", fg="green")
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(xsd_file, parser)
        type_overview.update(create_file_overview(tree.getroot()))
    return type_overview


def create_file_overview(root: Element) -> dict[str, list[FieldOverview]]:
    """Create an overview of the schema types in the given XSD file root element."""
    nsmap = {
        "xs": "http://www.w3.org/2001/XMLSchema",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }
    type_overview: dict[str, list[FieldOverview]] = {}

    for ct in root.findall("xs:complexType", nsmap):
        type_name = ct.get("name")
        if not type_name:
            continue

        complex_content = ct.find("xs:complexContent", nsmap)
        if complex_content is None:
            sequence = ct.find("xs:sequence", nsmap)
            choice = ct.find("xs:choice", nsmap)
        else:
            sequence = complex_content.find("xs:sequence", nsmap)
            choice = complex_content.find("xs:choice", nsmap)

        type_overview[type_name] = parse_complextype_fields(sequence or choice, nsmap)

    return type_overview


def parse_complextype_fields(complex_content: Element, nsmap: dict[str, str]) -> list[FieldOverview]:
    """Parse fields from the given complexContent element."""
    fields: list[FieldOverview] = []
    if complex_content is None:
        return fields
    for element in complex_content.findall("xs:element", nsmap):
        name = element.get("name", "")
        type_ = element.get("type", "multilingual" if is_multilingual(element) else "anonymous")
        required = element.get("minOccurs", "1") != "0"
        max_occurs = element.get("maxOccurs", "1")
        array = max_occurs == "unbounded" or (max_occurs.isdigit() and int(max_occurs) > 1)
        fields.append(
            FieldOverview(
                name=name,
                type=type_,
                required=required,
                array=array,
            )
        )
    return fields


if __name__ == "__main__":
    create_schema_overview()

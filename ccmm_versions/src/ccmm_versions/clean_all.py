"""Normalize XML Schema files.

The normalization removes annotations, sorts elements and attributes,
and cleans namespaces.
"""

from pathlib import Path

import click
from lxml import etree
from lxml.etree import _Element as Element


@click.command()
@click.argument("input_dir", type=click.Path())
@click.argument("output_dir", type=click.Path())
def clean_all(input_dir: str, output_dir: str) -> None:
    """Normalize all XML Schema files in the input directory and save to output directory."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for xsd_file in list(Path(input_dir).glob("**/*.xsd")):
        click.secho(f"Normalizing: {xsd_file}", fg="green")
        if xsd_file.resolve().is_relative_to(Path(output_dir).resolve()):
            continue
        relpath = xsd_file.relative_to(input_dir)
        outpath = Path(output_dir) / (relpath.parts[0] + ".xsd")
        normalize_xml_schema(xsd_file, outpath)


def normalize_xml_schema(input_xml: Path, output_xml: Path) -> None:
    """Normalize an XML Schema file."""
    # Parse the XML schema
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(input_xml, parser)
    root = tree.getroot()
    # Define namespaces we might encounter in schema files
    nsmap = {
        "xs": "http://www.w3.org/2001/XMLSchema",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }

    remove_annotation_elements(root, nsmap)
    remove_extension_lax_elements(root, nsmap)
    sort_attributes_by_name(root)
    sort_elements_by_name(root, nsmap)
    etree.cleanup_namespaces(root)

    # Serialize with consistent formatting
    Path(output_xml).write_text(
        etree.tostring(
            root,
            pretty_print=True,
            encoding="utf-8",
            xml_declaration=True,
            standalone=False,
        ).decode("utf-8")
    )


def remove_extension_lax_elements(root: Element, nsmap: dict) -> None:
    """Remove xs:any elements with 'lax' processContents from the XML schema."""
    # Remove all xs:any with processContents="lax"
    for el in root.xpath('//xs:any[@processContents="lax"]', namespaces=nsmap):
        el.getparent().remove(el)


def remove_annotation_elements(root: Element, nsmap: dict) -> None:
    """Remove annotation, include, and import elements from the XML schema."""
    # Remove all annotation elements (which contain documentation/appinfo)
    for el in root.xpath("//xs:annotation", namespaces=nsmap):
        el.getparent().remove(el)
    for el in root.xpath("//xs:include", namespaces=nsmap):
        el.getparent().remove(el)
    for el in root.xpath("//xs:import", namespaces=nsmap):
        el.getparent().remove(el)
    for el in root.xpath("//xs:import", namespaces=nsmap):
        el.getparent().remove(el)


def sort_attributes_by_name(root: Element) -> None:
    """Sort attributes of each element lexicographically and remove unnecessary ones."""
    for element in root.iter():
        if not isinstance(element, Element):
            continue  # comment, processing instruction, etc.

        # Get all attributes and sort them
        attrs = element.attrib
        if attrs:
            sorted_attrs = sorted(attrs.items())
            # Clear and re-add in sorted order
            element.attrib.clear()
            for name, value in sorted_attrs:
                val = value
                if name in (
                    "{http://www.w3.org/ns/sawsdl}modelReference",
                    "{http://www.w3.org/2007/XMLSchema-versioning}minVersion",
                    "targetNamespace",
                    "elementFormDefault",
                ):
                    # Skip attributes that are not needed
                    continue

                if name == "type" and ":" in value:
                    val = value.split(":")[-1]  # Keep only local name
                element.attrib[name] = val


def sort_elements_by_name(root: Element, nsmap: dict) -> None:
    """Sort xs:element children of each parent element by their name attribute."""
    # Define the namespace

    # Find all parent elements that contain xs:element children
    parents_with_elements = root.xpath("//*[xs:element]", namespaces=nsmap)

    for parent in parents_with_elements:
        # Get all xs:element children
        elements = parent.xpath("xs:element", namespaces=nsmap)

        # Skip if only one element (nothing to sort)
        if len(elements) <= 1:
            continue

        # Sort elements by their name attribute
        elements_sorted = sorted(
            elements,
            key=lambda el: el.get("name", "").lower(),  # Case-insensitive sort
        )

        # Remove all elements from parent (we'll re-add them in sorted order)
        for el in elements:
            parent.remove(el)

        # Add elements back in sorted order
        for el in elements_sorted:
            parent.append(el)


# Example usage:
if __name__ == "__main__":
    clean_all()

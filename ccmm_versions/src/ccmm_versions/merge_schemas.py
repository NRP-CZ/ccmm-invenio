"""Normalize XML Schema files.

The normalization removes annotations, sorts elements and attributes,
and cleans namespaces.
"""

from pathlib import Path
from typing import Any

import click
from lxml import etree
from lxml.etree import _Element as Element


@click.command()
@click.argument("input_dir", type=click.Path())
@click.argument("output_file", type=click.Path())
def merge_schemas(input_dir: str, output_file: str) -> None:
    """Normalize all XML Schema files in the input directory and save to output directory."""
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    root_elements = []
    for xsd_file in list(Path(input_dir).glob("**/*.xsd")):
        # the out directory is created by our cleaning steps, skip it
        if "out" in xsd_file.parts:
            continue
        click.secho(f"Concatenating: {xsd_file}", fg="green")
        root_elements.append(load_xml_schema(str(xsd_file)))
    first_root = root_elements[0]
    canonical_representations = {
        make_canonical_string(element)
        for element in first_root
        if getattr(element, "tag", None) is not None
    }
    for other_root in root_elements[1:]:
        # add attributes that are not present in the first root
        for attr_name, attr_value in other_root.attrib.items():
            if attr_name not in first_root.attrib:
                first_root.attrib[attr_name] = attr_value
        # add missing namespace declarations
        for ns_decl in other_root.nsmap.items():
            if ns_decl[0] not in first_root.nsmap:
                first_root = duplicate_with_new_namespace(
                    first_root, ns_decl[0], ns_decl[1]
                )
        for element in other_root:
            if getattr(element, "tag", None) is None:
                continue
            # check if the element is already present
            canonical_element = make_canonical_string(element)
            if canonical_element in canonical_representations:
                if element.tag != "{http://www.w3.org/2001/XMLSchema}import":
                    raise ValueError(
                        f"Duplicate element found that is not an import: {etree.tostring(element).decode('utf-8')}"
                    )
                continue
            canonical_representations.add(canonical_element)
            # if the element is xs:import, add it to the beginning
            if element.tag == "{http://www.w3.org/2001/XMLSchema}import":
                first_root.insert(0, element)
            else:
                first_root.append(element)
    tree = etree.ElementTree(first_root)
    tree.write(
        output_file,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )


def duplicate_with_new_namespace(
    element: Element, prefix: str | None, uri: str
) -> Element:
    """Duplicate the given element adding a new namespace declaration."""
    click.secho(f"Adding namespace declaration: {prefix} -> {uri}", fg="blue")
    new_attrib = {**element.attrib}
    # if prefix is None:
    #     new_attrib["xmlns"] = uri
    # else:
    #     new_attrib[f"xmlns:{prefix}"] = uri

    new_element = etree.Element(
        element.tag,
        attrib=new_attrib,
        nsmap=(
            {**element.nsmap, prefix: uri} if prefix else {**element.nsmap, None: uri}
        ),
    )
    for child in element:
        new_element.append(child)
    new_element.text = element.text
    new_element.tail = element.tail
    return new_element


def make_canonical_string(element: Element) -> Any:
    """Return a canonical string representation of the given XML element."""
    return etree.tostring(
        element,
        method="c14n",
        exclusive=True,
        with_comments=False,
        inclusive_ns_prefixes=None,
    ).decode("utf-8")


def load_xml_schema(file_path: str) -> Element:
    """Load an XML Schema from the given file path."""
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(file_path, parser)
    # remove xs:include from everywhere
    for include in tree.xpath(
        "//xs:include", namespaces={"xs": "http://www.w3.org/2001/XMLSchema"}
    ):
        parent = include.getparent()
        if parent is not None:
            parent.remove(include)
    return tree.getroot()


# Example usage:
if __name__ == "__main__":
    merge_schemas()

"""Identify anonymous types in XSD files."""

from pathlib import Path

import click
from lxml import etree
from lxml.etree import QName
from lxml.etree import _Element as Element


@click.command()
@click.argument("dirname", type=click.Path(exists=True, file_okay=False))
def identify_anonymous_types(dirname: str) -> None:
    """Identify anonymous types in XSD files in the given directory."""
    for xsd_file in Path(dirname).glob("*.xsd"):
        click.secho(f"Checking: {xsd_file}", fg="green")
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(xsd_file, parser)
        identify_anonymous_types_in_tree(tree.getroot(), xsd_file)


def has_tag(element: Element, namespace: str, tag: str) -> bool:
    """Check if the given element has the specified tag in the given namespace."""
    qn = QName(element)
    return qn.localname == tag and qn.namespace == namespace


def is_multilingual(element: Element) -> bool:
    """Check if the given type element is a multilingual type.

    Multilingual types look like:

    <xs:complexType> ... this is the input element
      <xs:simpleContent>
        <xs:extension base="xs:string">
          <xs:attribute ref="xml:lang"/>
        </xs:extension>
      </xs:simpleContent>
    </xs:complexType>
    """
    nsmap = {"xs": "http://www.w3.org/2001/XMLSchema"}

    # Check if element is a complexType
    ct = element.find("xs:complexType", nsmap)
    if not ct:
        return False
    # Look for simpleContent child
    simple_content = ct.find("xs:simpleContent", nsmap)
    if simple_content is None:
        return False
    # Look for extension child of simpleContent
    extension = simple_content.find("xs:extension", nsmap)
    if extension is None:
        return False
    # Check if extension base is xs:string
    base = extension.get("base")
    if base not in ("xs:string", "xsd:string"):
        return False
    # Look for xml:lang attribute
    attributes = extension.findall("xs:attribute", nsmap)
    return any(attr.get("ref") == "xml:lang" for attr in attributes)


def get_name_path(element: Element) -> str:
    """Get the hierarchical path of names leading to the given element."""
    path = []
    for ancestor in element.iterancestors():
        name = ancestor.get("name")
        tagname = QName(ancestor).localname
        if name:
            path.append(f"{tagname}[{name}]")
        else:
            path.append(f"{tagname}")
    path.reverse()
    return "/".join(path)


def identify_anonymous_types_in_tree(root: Element, _xsd_file: Path) -> None:
    """Identify and print anonymous types in the given XML tree."""
    nsmap = {
        "xs": "http://www.w3.org/2001/XMLSchema",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }
    elements_with_anonymous_types = root.xpath("//xs:element[xs:complexType or xs:simpleType]", namespaces=nsmap)

    for elem in elements_with_anonymous_types:
        type_child = elem.find("xs:complexType", nsmap)
        if is_multilingual(type_child):
            continue  # Skip multilingual types

        path = get_name_path(elem)
        click.secho(f"{path}:", fg="red")
        click.secho(etree.tostring(elem, pretty_print=True).decode("utf-8"))


if __name__ == "__main__":
    identify_anonymous_types()

# Local copies of the remote schemas imported by the CCMM XSD

The CCMM XSD imports GML 3.2.1 (`http://schemas.opengis.net/gml/3.2.1/gml.xsd`, which imports ISO 19139
and xlink) and `http://www.w3.org/2001/xml.xsd`. Loading them over the network made the schema build slow and
failed when schemas.opengis.net was down, so they are kept here as `<host>/<path>` of their URL and
`converter.get_ccmm_1_1_0_schema` maps the URLs to these files (no network access).

Downloaded unchanged on 2026-10-13 (all schemas reachable from the CCMM XSD imports/includes). The copyright
notices are in the files: GML and ISO 19139 schemas © Open Geospatial Consortium
(https://www.ogc.org/legal/), xml.xsd and xlink.xsd © W3C.

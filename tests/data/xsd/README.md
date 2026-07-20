# Offline test copy of the CCMM XSD

`ccmm-1.1.0-test.xsd` in this directory is a copy of
`ccmm_versions/merged/1.1.0-2026-01-29.xsd`, patched so that `lxml.etree.XMLSchema` can
compile it fully offline, for use by `tests/serializers/production/test_ccmm.py`
(schema-validation of `CCMMSerializer` output). It must stay semantically equivalent to
the upstream schema for everything `CCMMSerializer` actually produces. Three changes
were made:

1. **Removed the `xs:import` of the GML namespace** (`schemaLocation` pointing at
   `http://schemas.opengis.net/gml/3.2.1/gml.xsd`, which itself recursively includes a
   large chunk of the full OGC GML 3.2 schema) and the two GML-typed elements it
   enables: `location/bounding_box` (`gml:EnvelopeType`) and the raw-GML alternative to
   `wkt` on `geometry` (`gml:AbstractGeometry`). Both are optional (`minOccurs="0"`) and
   `CCMMSerializer.serialize_geometry` never emits either (it only ever emits `wkt`) --
   see `ccmm_export_plan.md`, "Locations". Fetching the real GML schema tree over the
   network on every test run would also make the test suite slow and flaky.

2. **Repointed the `xs:import` of the XML namespace** (needed for the `xml:lang`
   attribute used on every multilingual element) at the small vendored `xml.xsd` next
   to this file (copied from the `xmlschema` PyPI package's bundled copy,
   `xmlschema/schemas/XML/xml.xsd` -- that schema is small and has been stable for
   years) instead of fetching `http://www.w3.org/2001/xml.xsd` over the network. In
   this environment, `lxml.etree.XMLSchema()` fails to resolve that import over the
   network even though the URL itself is reachable (e.g. via `curl`/`urllib`) --
   `xmlSchemaParse`'s resource loading appears not to follow the same path as regular
   document parsing.

3. **Fixed a genuine authoring bug in the upstream `identifier` complex type.**: its
   trailing extensibility wildcard is `<xs:any minOccurs="0" maxOccurs="unbounded"
   processContents="lax"/>` with *no* `namespace` restriction (defaults to `##any`),
   unlike every other complex type in the file (all ~20 of them use `namespace="##other"`
   on the equivalent trailing wildcard). Because `##any` also matches the CCMM
   namespace itself, this overlaps with the preceding optional `authorized` element and
   violates the XSD Unique Particle Attribution constraint, which `lxml`/`libxml2`
   enforces strictly (`XMLSchemaParseError: complex type 'identifier': The content
   model is not determinist.`). Patched to `namespace="##other"`, matching every other
   complex type in the file. `CCMMSerializer` never emits unknown extension elements
   either way, so this has no effect on what we're testing.

If the upstream schema is regenerated, regenerate this file from it and re-apply the
same three changes (there is no automated script for this -- it's a handful of
`str.replace`s, done once).

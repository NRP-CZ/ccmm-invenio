import {
  Field,
  SchemaField,
} from "@js/invenio_rdm_records/src/deposit/serializers";


export const LocationsSchema = {
  place: new Field({ fieldpath: "place", deserializedDefault: "" }),
  description: new Field({ fieldpath: "description", deserializedDefault: "" }),
  identifiers: new SchemaField({
    fieldpath: "identifiers",
    schema: {
      scheme: new Field({ fieldpath: "scheme" }),
      identifier: new Field({ fieldpath: "identifier" }),
    },
    deserializedDefault: [],
  }),
  geometry: new Field({ fieldpath: "geometry", deserializedDefault: null }),
};
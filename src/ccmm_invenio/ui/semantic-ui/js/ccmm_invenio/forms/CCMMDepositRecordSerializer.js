import _cloneDeep from "lodash/cloneDeep";
import { SchemaField } from "@js/invenio_rdm_records/src/deposit/serializers";
import { RDMDepositRecordSerializer } from "@js/invenio_rdm_records/src/deposit/api/DepositRecordSerializer";
import { OARepoDepositSerializer } from "@js/oarepo_ui/api";
import { RelatedResourceSchema } from "./RelatedResourceField/RelatedResourceSchema";
import { LocationsSchema } from "./LocationsField/LocationsSchema";

const KEYS_TO_REMOVE = ["__key"];
const keyStripper = new OARepoDepositSerializer([], KEYS_TO_REMOVE);

export class CCMMDepositRecordSerializer extends RDMDepositRecordSerializer {
  get depositRecordSchema() {
    return {
      ...super.depositRecordSchema,
      related_resources: new SchemaField({
        fieldpath: "metadata.related_resources",
        schema: RelatedResourceSchema,
      }),
      locations: new SchemaField({
        fieldpath: "metadata.locations.features",
        schema: LocationsSchema,
        deserializedDefault: [],
      }),
    };
  }

  serialize(record) {
    const serialized = keyStripper.removeKeysFromNestedObjects(
      _cloneDeep(super.serialize(record)) || {},
      KEYS_TO_REMOVE
    );

    const features = serialized?.metadata?.locations?.features;
    if (Array.isArray(features)) {
      serialized.metadata.locations.features = features.map((feature) => {
        const cleaned = { ...feature };

        if (typeof cleaned.place !== "string" || cleaned.place.trim() === "") {
          cleaned.place = null;
        }

        if (!cleaned.geometry?.type || !cleaned.geometry?.coordinates) {
          cleaned.geometry = null;
        }

        return cleaned;
      });
    }

    return serialized;
  }
}
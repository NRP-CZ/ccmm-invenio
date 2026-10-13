import { SchemaField } from "@js/invenio_rdm_records/src/deposit/serializers";
import { RDMDepositRecordSerializer } from "@js/invenio_rdm_records/src/deposit/api/DepositRecordSerializer";
import { RelatedResourceSchema } from "./RelatedResourceField/RelatedResourceSchema";

export class CCMMDepositRecordSerializer extends RDMDepositRecordSerializer {
  get depositRecordSchema() {
    return {
      ...super.depositRecordSchema,
      related_resources: new SchemaField({
        fieldpath: "metadata.related_resources",
        schema: RelatedResourceSchema,
      }),
    };
  }

  /**
   * Serialize frontend Formik record to backend payload (stripping __key).
   */
  serialize(record) {
    const serializedRecord = super.serialize(record) || {};

    const locationsState = record?.metadata?.locations;
    if (
      locationsState &&
      locationsState.features &&
      Array.isArray(locationsState.features)
    ) {
      const cleanedFeatures = locationsState.features.map((feature) => {
        const { __key, ...cleanFeature } = feature;

        // Place if required field.
        if (!cleanFeature.place || cleanFeature.place.trim() === "") {
          cleanFeature.place = null;
        }

        // Valid geometry is also required.
        if (
          !cleanFeature.geometry ||
          !cleanFeature.geometry.type ||
          !cleanFeature.geometry.coordinates
        ) {
          cleanFeature.geometry = null;
        }

        if (
          cleanFeature.identifiers &&
          Array.isArray(cleanFeature.identifiers)
        ) {
          cleanFeature.identifiers = cleanFeature.identifiers.map((id) => {
            const { __key: idKey, ...cleanId } = id;
            return cleanId;
          });
        }

        return cleanFeature;
      });

      if (!serializedRecord.metadata) {
        serializedRecord.metadata = {};
      }
      serializedRecord.metadata.locations = {
        ...locationsState,
        features: cleanedFeatures,
      };
    }

    return serializedRecord;
  }

  /**
   * Deserialize backend payload to frontend Formik state (inject __key).
   */
  deserialize(record) {
    const deserializedRecord = super.deserialize(record) || {};

    const backendLocations = record?.metadata?.locations;

    if (
      backendLocations &&
      backendLocations.features &&
      Array.isArray(backendLocations.features)
    ) {
      const featuresWithKeys = backendLocations.features.map((feature) => {
        let identifiers = feature.identifiers || [];

        if (Array.isArray(identifiers)) {
          identifiers = identifiers.map((id) => ({
            ...id,
            __key: Math.random().toString(36).substring(7),
          }));
        }

        return {
          ...feature,
          identifiers,
          __key: Math.random().toString(36).substring(7),
        };
      });

      if (!deserializedRecord.metadata) {
        deserializedRecord.metadata = {};
      }
      deserializedRecord.metadata.locations = {
        ...backendLocations,
        features: featuresWithKeys,
      };
    }

    return deserializedRecord;
  }
}

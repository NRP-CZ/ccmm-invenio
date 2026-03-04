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
}

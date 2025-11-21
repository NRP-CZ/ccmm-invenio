from flask_resources import BaseListSchema, MarshmallowSerializer
from flask_resources.serializers import JSONSerializer
from invenio_rdm_records.resources.serializers.datacite import DataCite43Schema


class CCMMProductionDataCiteJSONSerializer_1_1_0(MarshmallowSerializer):
    """Marshmallow based DataCite serializer for records."""

    def __init__(self, **options):
        """Constructor."""
        super().__init__(
            format_serializer_cls=JSONSerializer,
            object_schema_cls=ProductionDataCiteSchema,
            list_schema_cls=BaseListSchema,
            schema_kwargs={},
            **options,
        )


class ProductionDataCiteSchema(DataCite43Schema):
    """Schema for DataCite serialization of CCMM production records.

    TODO: this will not work correctly !!!
    """

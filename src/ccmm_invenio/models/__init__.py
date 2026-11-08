# SPDX-FileCopyrightText: 2025-2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""The ccmm model preset (`ccmm_preset_1_1_0`, alias `ccmm_production_preset_1_1_0`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from invenio_i18n import lazy_gettext as _
from oarepo_model import from_yaml
from oarepo_model.api import FunctionalPreset
from oarepo_model.customizations import (
    AddMetadataExport,
    AddMetadataImport,
    AddToList,
    Customization,
    SetIndexNestedFieldsLimit,
    SetIndexTotalFieldsLimit,
)
from oarepo_model.presets import Preset
from oarepo_rdm.model.presets import rdm_minimal_preset
from oarepo_rdm.model.presets.rdm.resources.records.exports import RDMCompleteExportsPreset
from oarepo_rdm.model.presets.rdm.services.records.rdm_record_ui_schema import (
    RDMCompleteRecordUISchemaPreset,
)
from oarepo_rdm.model.presets.rdm_metadata import merge_metadata

from ..resources.deserializers import CCMMJSONDeserializer, DataCiteJSONDeserializer
from ..resources.deserializers.datacite import DATACITE_JSON_MIMETYPE
from ..resources.serializers import CCMMXMLSerializer
from ..resources.serializers.ccmm import CCMM_XML_MIMETYPE
from ..resources.serializers.json import JSONWithoutRelatedIdentifiersSerializer
from ..services.components import FetchIdentifiersComponent, RelatedIdentifiersComponent, RootRecordComponent
from .customizations import ReplaceExportSerializer

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from oarepo_model.api import PresetList
    from oarepo_model.builder import InvenioModelBuilder
    from oarepo_model.model import InvenioModel


def ccmm_types_1_1_0() -> dict[str, Any]:
    """Return the model types: the used CCMM types, the dataset (RDM based) and the vocabularies."""
    return {
        **from_yaml("1.1.0-2026-01-29/ccmm.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/ccmm-invenio.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/ccmm-vocabularies.yaml", __file__),
    }


class CCMMMetadataPreset(FunctionalPreset):
    """Preset adding the CCMM dataset (CCMMDataset) to the metadata of the model."""

    types = ccmm_types_1_1_0()
    metadata_type = "CCMMDataset"

    @override
    def before_invenio_model(self, params: dict[str, Any]) -> None:
        """Perform extra action before the Invenio model is created."""
        if "metadata_type" not in params:
            params["metadata_type"] = self.metadata_type
        params["types"].append(self.types)

    @override
    def before_populate_type_registry(
        self,
        model: InvenioModel,
        types: Sequence[dict[str, Any]],
        presets: PresetList,
        customizations: Sequence[Customization],
        params: dict[str, Any],
    ) -> None:
        """Perform extra action before populating the type registry."""
        metadata_type = params["metadata_type"]
        # merge_metadata modifies the type dicts in place (not the list), a list copy shares them
        merge_metadata(list(types), metadata_type, self.metadata_type)


class CCMMExportPreset(Preset):
    """Preset adding the CCMM XML export (also OAI-PMH)."""

    modifies = ("exports",)

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Apply the preset."""
        yield AddMetadataExport(
            code="ccmm-xml",
            name=_("CCMM export"),
            mimetype=CCMM_XML_MIMETYPE,
            # the mimetype guess maps +xml types to .xsl
            extension=".xml",
            serializer=CCMMXMLSerializer(),
            oai_metadata_prefix="ccmm",
            oai_namespace="https://schema.ccmm.cz/research-data/1.1",
        )


class CCMMImportPreset(Preset):
    """Preset for CCMM imports."""

    modifies = ("imports",)

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Apply the preset."""
        yield AddMetadataImport(
            code="ccmm-xml",
            name=_("CCMM import"),
            mimetype=CCMM_XML_MIMETYPE,
            description=_("CCMM XML import."),
            deserializer=CCMMJSONDeserializer(),
            oai_name=("https://schema.ccmm.cz/research-data/1.1", "dataset"),
        )
        yield AddMetadataImport(
            code="datacite-json",
            name=_("DataCite JSON import"),
            mimetype=DATACITE_JSON_MIMETYPE,
            description=_("DataCite JSON import (the attributes object of the DataCite REST API)."),
            deserializer=DataCiteJSONDeserializer(),
        )


class CCMMRootRecordComponentPreset(Preset):
    """Preset for CCMM root record components."""

    modifies = ("record_service_components",)

    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Yield component."""
        _, _, _ = builder, model, dependencies
        yield AddToList("record_service_components", RootRecordComponent)


class CCMMRelatedIdentifiersComponentPreset(Preset):
    """Preset deriving the RDM related identifiers from the ccmm related resources (see RelatedIdentifiersComponent)."""

    modifies = ("record_service_components",)

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Yield component."""
        _, _, _ = builder, model, dependencies
        yield AddToList("record_service_components", RelatedIdentifiersComponent)


class CCMMFetchIdentifiersComponentPreset(Preset):
    """Preset creating the vocabulary records missing for a record (see FetchIdentifiersComponent)."""

    modifies = ("record_service_components",)

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Yield component."""
        _, _, _ = builder, model, dependencies
        yield AddToList("record_service_components", FetchIdentifiersComponent)


class CCMMHideRelatedIdentifiersPreset(Preset):
    """Preset removing the RDM related identifiers from the application/json export (provided by ExportsPreset).

    They are derived from the related resources (see CCMMRelatedIdentifiersComponentPreset) for RDM;
    the API clients see the related resources. The UI JSON (read only) keeps them.
    """

    modifies = ("exports",)

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Yield the customization."""
        _, _, _ = builder, model, dependencies
        yield ReplaceExportSerializer("json", JSONWithoutRelatedIdentifiersSerializer())


class RootRecordFieldPreset(FunctionalPreset):
    """Record type functional preset."""

    @override
    def before_invenio_model(self, params: dict[str, Any]) -> None:
        """Perform extra action before the Invenio model is created."""
        if "record_type" not in params or params["record_type"] is None:
            params["record_type"] = "CCMMRootRecord"


class CCMMIndexSettingsPreset(Preset):
    """Preset that sets minimal index size limits for ccmm models."""

    modifies = ("record-mapping",)

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        yield SetIndexTotalFieldsLimit(2000)
        yield SetIndexNestedFieldsLimit(200)


ccmm_preset_1_1_0 = [
    *rdm_minimal_preset,
    RDMCompleteRecordUISchemaPreset,
    CCMMMetadataPreset,
    CCMMImportPreset,
    CCMMIndexSettingsPreset,
    CCMMExportPreset,
    RDMCompleteExportsPreset,
    RootRecordFieldPreset,
    CCMMRootRecordComponentPreset,
    CCMMRelatedIdentifiersComponentPreset,
    CCMMFetchIdentifiersComponentPreset,
    CCMMHideRelatedIdentifiersPreset,
]

ccmm_production_preset_1_1_0 = ccmm_preset_1_1_0
"""Alias of ccmm_preset_1_1_0, kept for compatibility."""

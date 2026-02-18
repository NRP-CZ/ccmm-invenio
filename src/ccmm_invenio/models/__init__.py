#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""ccmm-invenio preset."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from flask_resources.deserializers import DeserializerMixin
from invenio_access.permissions import system_identity
from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.records.components import ServiceComponent
from invenio_vocabularies.proxies import current_service as vocabulary_service
from lxml.etree import fromstring
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
from oarepo_model.model import InvenioModel
from oarepo_model.presets import Preset
from oarepo_rdm.model.presets import rdm_minimal_preset
from oarepo_rdm.model.presets.rdm_metadata import merge_metadata

from ccmm_invenio.parsers.production_1_1_0 import CCMMXMLProductionParser

from ..serializers import (
    CCMMNMADataCiteJSONSerializer_1_1_0,
    CCMMProductionDataCiteJSONSerializer_1_1_0,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from flask_principal import Identity
    from invenio_records.api import Record
    from oarepo_model.builder import InvenioModelBuilder
    from oarepo_model.model import InvenioModel


def ccmm_1_1_0() -> dict[str, Any]:
    """Return RDM specific model types."""
    return {
        **from_yaml("1.1.0-2026-01-29/ccmm.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/ccmm-vocabularies.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/geojson-1.1.0.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/gml-1.1.0.yaml", __file__),
    }


def ccmm_production_1_1_0() -> dict[str, Any]:
    """Return RDM specific model types."""
    return {
        **from_yaml("1.1.0-2026-01-29/ccmm.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/ccmm-invenio.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/ccmm-vocabularies.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/geojson-1.1.0.yaml", __file__),
        **from_yaml("1.1.0-2026-01-29/gml-1.1.0.yaml", __file__),
    }


class CCMMBaseMetadataPreset(FunctionalPreset):
    """Preset for CCMM metadata."""

    types: dict[str, Any]
    metadata_type: str

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
        types: list[dict[str, Any]],
        presets: list[type[Preset] | list[type[Preset]] | tuple[type[Preset]]],
        customizations: list[Customization],
        params: dict[str, Any],
    ) -> None:
        """Perform extra action before populating the type registry."""
        metadata_type = params["metadata_type"]
        merge_metadata(types, metadata_type, self.metadata_type)


class CCMMProductionCustomizationPreset(Preset):
    """Preset for CCMM production metadata customizations."""

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
            code="datacite",
            name=_("Datacite export"),
            mimetype="application/vnd.datacite.datacite+json",
            serializer=CCMMProductionDataCiteJSONSerializer_1_1_0(),
        )


class CCMMProductionDeserializer(DeserializerMixin):
    """CCMM Invenio metadata deserializer."""

    def __init__(self, parser: type[CCMMXMLProductionParser], vocabulary_loader: Any):
        """Construct."""
        self.parser = parser
        self.vocabulary_loader = vocabulary_loader
        super().__init__()

    def deserialize(self, data: bytes) -> dict:
        """Deserialize data."""
        root_el = fromstring(data)
        return self.parser(vocabulary_loader=self.vocabulary_loader).parse(root_el)


def invenio_vocabulary_loader(vocabulary_type: str, iri: str) -> str:
    """Load vocabulary from IRI."""
    if vocabulary_type == "resourcerelationtypes":
        vocabulary_type = "relationtypes"

    # TODO: add mediatypes to IRI
    if vocabulary_type == "mediatypes":
        return iri
    if vocabulary_type == "fileformats":
        vocabulary_type = "filetypes"

    hits = vocabulary_service.search(identity=system_identity, type=vocabulary_type, params={"q": f'props.iri:"{iri}"'})
    if hits.total == 0:
        raise KeyError(f"iri {iri} not found for {vocabulary_type}")

    voc = next(hits.hits)
    return str(voc["id"])


class SetCCMMImport(Customization):
    """Set importer."""

    def __init__(self, parser: type[CCMMXMLProductionParser], vocabulary_loader: Any):
        """Construct importer with optional custom parser."""
        self.parser = parser
        self.vocabulary_loader = vocabulary_loader
        super().__init__(name="SetCCMMImport")

    def apply(self, builder: InvenioModelBuilder, model: InvenioModel) -> None:
        """Apply importer with optional custom parser."""
        AddMetadataImport(
            code="ccmm-xml",
            name=_("CCMM import"),
            mimetype="application/vnd.ccmm+xml",
            description=_("CCMM XML export."),
            deserializer=CCMMProductionDeserializer(parser=self.parser, vocabulary_loader=self.vocabulary_loader),
            oai_name=("https://schema.ccmm.cz/research-data/1.1", "dataset"),
        ).apply(builder, model)


class CCMMImportPreset(Preset):
    """Preset for CCMM imports."""

    @override
    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Apply the preset."""
        yield SetCCMMImport(parser=CCMMXMLProductionParser, vocabulary_loader=invenio_vocabulary_loader)


class CCMMNMACustomizationPreset(Preset):
    """Preset for CCMM production metadata customizations."""

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
            code="datacite",
            name=_("Datacite export"),
            mimetype="application/vnd.datacite.datacite+json",
            serializer=CCMMNMADataCiteJSONSerializer_1_1_0(),
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

        class RootRecordComponent(ServiceComponent):
            def create(
                self,
                identity: Identity,
                data: dict | None = None,
                record: Record | None = None,
                errors: list | None = None,
                **kwargs: Any,
            ) -> None:
                """Inject parsed metadata to the record."""
                _, _, _ = identity, errors, kwargs
                if data is not None and record is not None:
                    record["ccmm_xml"] = data.get("ccmm_xml", "")

        yield AddToList("record_service_components", RootRecordComponent)


class CCMMProductionPreset(CCMMBaseMetadataPreset):
    """Preset for CCMM production metadata."""

    types = ccmm_production_1_1_0()
    metadata_type = "CCMMDataset"


class CCMMNMAPreset(CCMMBaseMetadataPreset):
    """Preset for CCMM production metadata."""

    types = ccmm_1_1_0()
    metadata_type = "CCMMDataSet"


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


ccmm_nma_preset_1_1_0 = [
    *rdm_minimal_preset,
    CCMMNMAPreset,
    CCMMIndexSettingsPreset,
    CCMMNMACustomizationPreset,
]

ccmm_production_preset_1_1_0 = [
    *rdm_minimal_preset,
    CCMMProductionPreset,
    CCMMImportPreset,
    CCMMIndexSettingsPreset,
    CCMMProductionCustomizationPreset,
    RootRecordFieldPreset,
    CCMMRootRecordComponentPreset,
]

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

from oarepo_model import from_yaml
from oarepo_model.api import FunctionalPreset
from oarepo_model.customizations import (
    Customization,
    IndexNestedFieldsLimit,
    IndexTotalFieldsLimit,
)
from oarepo_model.model import InvenioModel
from oarepo_model.presets import Preset
from oarepo_rdm.model.presets import rdm_minimal_preset
from oarepo_rdm.model.presets.rdm_metadata import merge_metadata

if TYPE_CHECKING:
    from collections.abc import Generator

    from oarepo_model.builder import InvenioModelBuilder
    from oarepo_model.customizations import Customization
    from oarepo_model.model import InvenioModel


def ccmm_1_1_0() -> dict[str, Any]:
    """Return RDM specific model types."""
    return {
        **from_yaml("1.1.0a1-2025-11-03/ccmm.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/ccmm-vocabularies.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/geojson-1.1.0.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/gml-1.1.0.yaml", __file__),
    }


def ccmm_production_1_1_0() -> dict[str, Any]:
    """Return RDM specific model types."""
    return {
        **from_yaml("1.1.0a1-2025-11-03/ccmm.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/ccmm-invenio.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/ccmm-vocabularies.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/geojson-1.1.0.yaml", __file__),
        **from_yaml("1.1.0a1-2025-11-03/gml-1.1.0.yaml", __file__),
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


class CCMMProductionPreset(CCMMBaseMetadataPreset):
    """Preset for CCMM production metadata."""

    types = ccmm_production_1_1_0()
    metadata_type = "CCMMProductionDataset"


class CCMMNMAPreset(CCMMBaseMetadataPreset):
    """Preset for CCMM production metadata."""

    types = ccmm_1_1_0()
    metadata_type = "CCMMDataSet"


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
        yield IndexTotalFieldsLimit(2000)
        yield IndexNestedFieldsLimit(200)


ccmm_nma_preset_1_1_0 = [*rdm_minimal_preset, CCMMNMAPreset, CCMMIndexSettingsPreset]

ccmm_production_preset_1_1_0 = [
    *rdm_minimal_preset,
    CCMMProductionPreset,
    CCMMIndexSettingsPreset,
]

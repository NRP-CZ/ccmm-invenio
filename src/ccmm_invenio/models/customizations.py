# SPDX-FileCopyrightText: 2025-2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""oarepo-model customizations of the ccmm presets."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, override

from oarepo_model.customizations import Customization

if TYPE_CHECKING:
    from flask_resources.serializers import BaseSerializer
    from oarepo_model.builder import InvenioModelBuilder
    from oarepo_model.model import InvenioModel


class ReplaceExportSerializer(Customization):
    """Replace the serializer of an export of the model, found by its code (e.g. "json")."""

    def __init__(self, code: str, serializer: BaseSerializer) -> None:
        """Create the customization."""
        super().__init__("exports")
        self._code = code
        self._serializer = serializer

    @override
    def apply(self, builder: InvenioModelBuilder, model: InvenioModel) -> None:
        exports = builder.get_list("exports")
        for idx, export in enumerate(exports):
            if export.code == self._code:
                exports[idx] = dataclasses.replace(export, serializer=self._serializer)
                return
        raise KeyError(f"No export with code {self._code!r} to replace the serializer of")

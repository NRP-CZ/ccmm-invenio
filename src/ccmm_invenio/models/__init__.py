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

import mimetypes
from typing import TYPE_CHECKING, Any, override

from flask_resources.deserializers import DeserializerMixin
from invenio_access.permissions import system_identity
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.resources.config import csl_url_args_retriever
from invenio_rdm_records.resources.serializers import (
    CSLJSONSerializer,  # type: ignore[reportAttributeAccessIssue]
    StringCitationSerializer,  # type: ignore[reportAttributeAccessIssue]
)
from invenio_rdm_records.resources.serializers.utils import convert_size
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
        yield AddMetadataExport(
            code="citation",
            name=_("Citation"),
            mimetype="text/x-bibliography",
            serializer=StringCitationSerializer(url_args_retriever=csl_url_args_retriever),
            display=False,
        )
        yield AddMetadataExport(
            code="citation-json",
            name=_("Citation"),
            mimetype="application/vnd.citationstyles.csl+json",
            serializer=CSLJSONSerializer(),
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


class CCMMSizesAndFormatsFromFilesComponentPreset(Preset):
    """Preset for auto-populating sizes and formats from uploaded files.

    This component automatically populates the 'sizes' and 'formats' metadata fields
    from the uploaded files' byte_size and mimetype.
    """

    modifies = ("record_service_components",)

    def apply(
        self,
        builder: InvenioModelBuilder,
        model: InvenioModel,
        dependencies: dict[str, Any],
    ) -> Generator[Customization]:
        """Yield component for auto-populating sizes and formats from files."""
        _, _, _ = builder, model, dependencies

        # Mapping of compression encodings to MIME types
        # mimetypes.guess_type() returns (None, encoding) for compressed files
        _ENCODING_TO_MIME = {
            "gzip": "application/gzip",
            "bzip2": "application/x-bzip2",
            "xz": "application/x-xz",
            "compress": "application/x-compress",
            "br": "application/brotli",
        }

        def _get_mime_type(filename: str) -> str | None:
            """Get MIME type for a filename using Python's mimetypes module.

            Handles both regular files and compression formats (.gz, .bz2, .xz, etc.).
            """
            mime_type, encoding = mimetypes.guess_type(filename)
            if mime_type:
                return mime_type
            if encoding:
                return _ENCODING_TO_MIME.get(encoding)
            return None

        class SizesAndFormatsFromFilesComponent(ServiceComponent):
            """Automatically populate sizes and formats from uploaded files."""

            def create(self, identity: Identity, **kwargs: Any) -> None:
                """Populate sizes and formats when creating a record."""
                data = kwargs.get("data")
                if data is not None:
                    self._populate_metadata(data)

            def update(self, identity: Identity, **kwargs: Any) -> None:
                """Populate sizes and formats when updating a record."""
                data = kwargs.get("data")
                if data is not None:
                    self._populate_metadata(data)

            def publish(
                self,
                identity: Identity,
                draft: Record | None = None,
                record: Record | None = None,
            ) -> None:
                """Populate sizes and formats when publishing a draft.

                This is called during draft publication when files should be fully attached.
                We update the draft's metadata with file sizes and formats before publishing.
                """
                if draft is None:
                    return
                self._populate_from_draft(draft)

            @staticmethod
            def _populate_metadata(data: dict[str, Any]) -> None:
                """Extract sizes and formats from file metadata.

                Extracts file sizes and MIME types from uploaded files and populates
                the metadata.sizes and metadata.formats fields.
                """
                metadata = data.get("metadata", {})
                files_entries = None

                if "files" in data and isinstance(data["files"], dict):
                    files_entries = data["files"].get("entries", {})

                if not files_entries:
                    return

                sizes = []
                formats = set()

                for file_info in files_entries.values():
                    if not isinstance(file_info, dict):
                        continue

                    # Get byte size
                    byte_size = file_info.get("size", 0)
                    if byte_size > 0:
                        sizes.append(convert_size(byte_size))

                    # Get MIME type
                    mime_type = file_info.get("mimetype") or file_info.get("media_type")
                    if mime_type:
                        formats.add(mime_type)

                if sizes:
                    metadata["sizes"] = sizes
                if formats:
                    metadata["formats"] = sorted(formats)

                data["metadata"] = metadata

            @staticmethod
            def _populate_from_draft(draft: Record) -> None:
                """Populate sizes and formats from draft's file objects.

                Accesses the draft's files attribute which contains the actual
                file metadata including size and mimetype.
                """
                if not hasattr(draft, "files") or not draft.files:
                    return

                files_manager = draft.files
                metadata = draft.get("metadata", {}) or {}

                sizes = []
                formats = set()

                for file_key, file_obj in files_manager.items():
                    # Get byte size
                    byte_size = file_obj.get("size", 0)
                    if byte_size > 0:
                        sizes.append(convert_size(byte_size))

                    # Get MIME type
                    mime_type = file_obj.get("mimetype") or file_obj.get("media_type")
                    if not mime_type and file_key:
                        mime_type = _get_mime_type(file_key)
                    if mime_type:
                        formats.add(mime_type)

                if sizes:
                    metadata["sizes"] = sizes
                if formats:
                    metadata["formats"] = sorted(formats)

                draft["metadata"] = metadata

        yield AddToList("record_service_components", SizesAndFormatsFromFilesComponent)


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
    CCMMSizesAndFormatsFromFilesComponentPreset,
]

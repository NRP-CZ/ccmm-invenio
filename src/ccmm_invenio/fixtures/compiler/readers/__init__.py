#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Readers turning external vocabulary sources into RDF graphs."""

from __future__ import annotations

from .access_rights import COARAccessRightsReader
from .base import RehomingReader, VocabularyReader
from .ccmm import CCMMCodelistReader
from .checksum_algorithms import SPDXChecksumAlgorithmsReader
from .curated import CuratedVocabularyReader
from .datacite import DataciteReader
from .date_types import (
    CCMMDateTypesReader,
    DateTypesMerger,
    RDMDateTypesReader,
)
from .description_types import (
    CCMMDescriptionTypesReader,
    DescriptionTypesMerger,
    RDMDescriptionTypesReader,
)
from .file_formats import EUFileFormatsReader
from .identifier_schemes import IdentifiersMerger, RDMIdentifierSchemesReader
from .inspire_themes import INSPIRE_SCHEME, InspireThemesReader
from .languages import LanguageReader, PrimaryLanguagesReader
from .licenses import LicensesMerger, RDMLicensesReader
from .location_relations import CCMMLocationRelationsReader
from .media_types import IANAMediaTypesReader
from .overlay import OverlayReader
from .rdm_fixture import RDMDataciteFixtureReader, RDMFixtureReader
from .relation_types import (
    CCMMRelationTypeReader,
    DataciteRelationTypeReader,
    RelationTypesMerger,
)
from .removal_reasons import RDMRemovalReasonsReader
from .resource_types import (
    COARResourceTypesReader,
    RDMResourceTypesReader,
    ResourceTypesMerger,
)
from .roles import (
    CCMMRolesReader,
    RDMRolesReader,
    RolesMerger,
)
from .skosmos import SkosmosReader
from .sssom import SSSOMMappingsReader
from .subjects import SUBJECT_SCHEME, SubjectsReader
from .title_types import (
    CCMMTitleTypesReader,
    RDMTitleTypesReader,
    TitleTypesMerger,
)

__all__ = [
    "INSPIRE_SCHEME",
    "SUBJECT_SCHEME",
    "CCMMCodelistReader",
    "CCMMDateTypesReader",
    "CCMMDescriptionTypesReader",
    "CCMMLocationRelationsReader",
    "CCMMRelationTypeReader",
    "CCMMRolesReader",
    "CCMMTitleTypesReader",
    "COARAccessRightsReader",
    "COARResourceTypesReader",
    "CuratedVocabularyReader",
    "DataciteReader",
    "DataciteRelationTypeReader",
    "DateTypesMerger",
    "DescriptionTypesMerger",
    "EUFileFormatsReader",
    "IANAMediaTypesReader",
    "IdentifiersMerger",
    "InspireThemesReader",
    "LanguageReader",
    "LicensesMerger",
    "OverlayReader",
    "PrimaryLanguagesReader",
    "RDMDataciteFixtureReader",
    "RDMDateTypesReader",
    "RDMDescriptionTypesReader",
    "RDMFixtureReader",
    "RDMIdentifierSchemesReader",
    "RDMLicensesReader",
    "RDMRemovalReasonsReader",
    "RDMResourceTypesReader",
    "RDMRolesReader",
    "RDMTitleTypesReader",
    "RehomingReader",
    "RelationTypesMerger",
    "ResourceTypesMerger",
    "RolesMerger",
    "SPDXChecksumAlgorithmsReader",
    "SSSOMMappingsReader",
    "SkosmosReader",
    "SubjectsReader",
    "TitleTypesMerger",
    "VocabularyReader",
]

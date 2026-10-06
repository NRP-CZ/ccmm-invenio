#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Reader for the location relation vocabulary."""

from __future__ import annotations

from .ccmm import CCMMCodelistReader


class CCMMLocationRelationsReader(CCMMCodelistReader):
    """Reader for the location relations published by techlib's CCMM registry.

    The source (``https://vocabs.ccmm.cz/registry/codelist/LocationRelation``)
    is a flat Skosmos codelist whose concepts carry language-tagged prefLabels
    (cs, en); they express how a resource relates to a location (stored at,
    collected in, processed at, ...). Neither InvenioRDM nor DataCite has a
    counterpart vocabulary - the concepts are re-homed into the NMA
    locationrelations namespace under their lowercased names (see
    :meth:`add_concept`) and used as-is.
    """

    vocabulary_type = "locationrelations"

    def __init__(self, uri: str = "https://vocabs.ccmm.cz/registry/codelist/LocationRelation/"):
        """Initialize the reader with the given URI."""
        super().__init__(uri)

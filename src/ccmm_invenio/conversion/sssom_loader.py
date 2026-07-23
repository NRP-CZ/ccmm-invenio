#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Load SSSOM mapping files into RDF triplestore."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, override

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, SKOS
from sssom.parsers import parse_sssom_table
from sssom.writers import write_rdf

from .loader import VocabularyLoader

if TYPE_CHECKING:
    from ccmm_invenio.conversion.rdf_store import RDFTripleStore

log = logging.getLogger(__name__)


class SSSOMLoader(VocabularyLoader):
    """Load SSSOM (Simple Standard for Sharing Ontology Mappings) files into RDF."""

    @override
    def load(self, uri: str, store: RDFTripleStore) -> int:
        """Load a single SSSOM TSV file into the triplestore.

        SSSOM files are TSV files with metadata in comments and mapping data in columns.
        This method uses the sssom library to parse and convert to RDF.
        """
        sssom_path = Path(uri)
        log.info("Loading SSSOM file: %s", sssom_path)

        if not sssom_path.exists():
            log.error("SSSOM file not found: %s", sssom_path)
            return 0

        # Parse SSSOM file
        msdf = parse_sssom_table(str(sssom_path))

        # Convert to RDF graph using sssom library
        rdf_graph = Graph()

        # Write to RDF using sssom's writer
        # The write_rdf function can write directly to a file or string
        # We'll use it to generate RDF and then parse it

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Write RDF to temporary file
            write_rdf(msdf, tmp_path)

            # Parse the RDF into our graph
            rdf_graph.parse(str(tmp_path), format="turtle")

        finally:
            # Clean up temporary file
            if tmp_path.exists():
                tmp_path.unlink()

        # Merge into main store
        before_count = store.size()

        # Extract direct SKOS.exactMatch relationships from the axiom-wrapped format
        # SSSOM creates owl:Axiom wrappers, but we want direct skos:exactMatch triples
        for axiom in rdf_graph.subjects(OWL.annotatedProperty, SKOS.exactMatch):
            source = rdf_graph.value(axiom, OWL.annotatedSource)
            target = rdf_graph.value(axiom, OWL.annotatedTarget)
            if source and target:
                store.graph.add((URIRef(str(source)), SKOS.exactMatch, URIRef(str(target))))

        store.merge(rdf_graph)
        after_count = store.size()
        added = after_count - before_count

        log.info("Loaded %d triples from SSSOM file %s", added, sssom_path.name)

        return 0

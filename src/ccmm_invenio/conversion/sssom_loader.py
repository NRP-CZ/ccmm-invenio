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
from pathlib import Path
from typing import TYPE_CHECKING

from rdflib import Graph

if TYPE_CHECKING:
    from ccmm_invenio.conversion.rdf_store import RDFTripleStore

log = logging.getLogger(__name__)


class SSSOMLoader:
    """Load SSSOM (Simple Standard for Sharing Ontology Mappings) files into RDF."""

    def __init__(self, store: RDFTripleStore) -> None:
        """Initialize the SSSOM loader.

        Args:
            store: The RDF triplestore to load mappings into

        """
        self.store = store

    def load_sssom_file(self, sssom_path: Path) -> int:
        """Load a single SSSOM TSV file into the triplestore.

        SSSOM files are TSV files with metadata in comments and mapping data in columns.
        This method uses the sssom library to parse and convert to RDF.

        Args:
            sssom_path: Path to the SSSOM TSV file

        Returns:
            Number of triples loaded

        """
        log.info("Loading SSSOM file: %s", sssom_path)

        if not sssom_path.exists():
            log.error("SSSOM file not found: %s", sssom_path)
            return 0

        try:
            # Import sssom library
            from sssom.parsers import parse_sssom_table
            from sssom.writers import write_rdf

            # Parse SSSOM file
            msdf = parse_sssom_table(str(sssom_path))

            # Convert to RDF graph using sssom library
            rdf_graph = Graph()

            # Write to RDF using sssom's writer
            # The write_rdf function can write directly to a file or string
            # We'll use it to generate RDF and then parse it
            import tempfile

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
            before_count = self.store.size()
            self.store.merge(rdf_graph)
            after_count = self.store.size()
            added = after_count - before_count

            log.info("Loaded %d triples from SSSOM file %s", added, sssom_path.name)

        except ImportError:
            log.exception("sssom library not available. Install with: pip install sssom")
            return 0
        except Exception:
            log.exception("Error loading SSSOM file: %s", sssom_path)
            return 0
        else:
            return added

    def load_directory(
        self,
        directory: Path,
        pattern: str = "*.tsv",
    ) -> dict[str, int]:
        """Load all SSSOM files matching a pattern from a directory.

        Args:
            directory: Directory containing SSSOM files
            pattern: Glob pattern for SSSOM files (default: "*.tsv")

        Returns:
            Dictionary mapping file names to number of triples loaded

        """
        log.info("Loading SSSOM files from directory: %s (pattern: %s)", directory, pattern)

        if not directory.exists() or not directory.is_dir():
            log.error("Directory not found or not a directory: %s", directory)
            return {}

        results = {}
        sssom_files = sorted(directory.glob(pattern))

        if not sssom_files:
            log.warning("No SSSOM files found in %s matching pattern %s", directory, pattern)
            return results

        for sssom_file in sssom_files:
            try:
                count = self.load_sssom_file(sssom_file)
                results[sssom_file.name] = count
            except Exception:
                log.exception("Error loading SSSOM file: %s", sssom_file)
                results[sssom_file.name] = 0

        total = sum(results.values())
        log.info("Loaded total of %d triples from %d SSSOM files", total, len(results))

        return results

    def load_mapping_set(
        self,
        sssom_files: list[Path],
    ) -> int:
        """Load a set of related SSSOM mapping files.

        Args:
            sssom_files: List of SSSOM file paths to load

        Returns:
            Total number of triples loaded

        """
        total = 0

        for sssom_file in sssom_files:
            count = self.load_sssom_file(sssom_file)
            total += count

        log.info("Loaded %d triples from %d SSSOM files", total, len(sssom_files))
        return total

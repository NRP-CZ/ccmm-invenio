#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Convert vocabularies from various sources to YAML fixtures.

This script performs the following steps:

1. Initialize a RDF triplestore
2. Load the input data from the `input` directory, converting them to a RDF triplet store
3. Load the data from spartql into the same triplestore
4. Load the input/sssom, convert it to a RDF triplet store, and merge it into the triplestore
5. Create invenio fixtures from the triplestore
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

from ccmm_invenio.conversion.csv_loader import CSVToRDFLoader
from ccmm_invenio.conversion.fixture_generator import FixtureGenerator
from ccmm_invenio.conversion.rdf_store import RDFTripleStore
from ccmm_invenio.conversion.sparql_loader import SPARQLLoader
from ccmm_invenio.conversion.sssom_loader import SSSOMLoader
from ccmm_invenio.conversion.utils import print_concept_schemes, print_statistics

log = logging.getLogger(__name__)


@click.command()
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing input CSV files",
)
@click.option(
    "--sssom-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing SSSOM mapping files",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to write output fixtures",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set the logging level",
)
def convert_vocabularies(
    input_dir: Path | None,
    sssom_dir: Path | None,
    output_dir: Path | None,
    log_level: str,
) -> None:
    """Convert vocabularies from various sources to YAML fixtures.

    This command orchestrates the vocabulary conversion process:
    1. Initializes an RDF triplestore
    2. Loads CSV vocabulary files from the input directory
    3. Loads vocabulary data from SPARQL endpoints/RDF files
    4. Loads SSSOM mapping files
    5. Generates Invenio YAML fixtures from the triplestore
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Determine directories relative to this file
    root_dir = Path(__file__).parent.parent
    input_dir = input_dir or root_dir / "input"
    sssom_dir = sssom_dir or root_dir / "input" / "sssom"
    output_dir = output_dir or root_dir / "fixtures"

    log.info("Starting vocabulary conversion")
    log.info("Input directory: %s", input_dir)
    log.info("SSSOM directory: %s", sssom_dir)
    log.info("Output directory: %s", output_dir)

    # Step 1: Initialize a RDF triplestore
    log.info("Step 1: Initializing RDF triplestore")
    store = RDFTripleStore()
    log.info("Triplestore initialized with %d triples", store.size())

    # Step 2: Load the input data from the `input` directory
    log.info("Step 2: Loading CSV input data")
    csv_loader = CSVToRDFLoader(store)

    # Load CSV vocabulary files
    csv_pattern = "CCMM_slovniky*.csv"
    csv_results = csv_loader.load_directory(input_dir, pattern=csv_pattern)

    log.info("CSV loading results:")
    for filename, count in csv_results.items():
        log.info("  - %s: %d concepts", filename, count)

    total_csv_concepts = sum(csv_results.values())
    log.info("Total concepts loaded from CSV: %d", total_csv_concepts)
    log.info("Triplestore now contains %d triples", store.size())

    # Step 3: Load data from SPARQL endpoints
    log.info("Step 3: Loading vocabulary data from SPARQL/RDF sources")
    sparql_loader = SPARQLLoader(store)

    # Define SPARQL/RDF sources
    sparql_results = {}

    # Languages from EU Publications Office (download RDF and query locally)
    try:
        log.info("Loading Languages from EU Publications Office...")
        count = sparql_loader.load_from_sparql_endpoint(
            endpoint="http://publications.europa.eu/resource/authority/language",
            scheme_uri="http://publications.europa.eu/resource/authority/language",
            load_subgraphs=True,  # Load individual concept URIs for full label data
            extra_props={
                "ISO_639_2T": """
                    ?concept skos:notation ?ISO_639_2T FILTER(datatype(?ISO_639_2T) = euvoc:ISO_639_2T)
                """,
                "ISO_639_1": """
                    ?concept skos:notation ?ISO_639_1 FILTER(datatype(?ISO_639_1) = euvoc:ISO_639_1)
                """,
                "ISO_639_3": """
                    ?concept skos:notation ?ISO_639_3 FILTER(datatype(?ISO_639_3) = euvoc:ISO_639_3)
                """,
                "XML_LNG": """
                    ?concept skos:notation ?XML_LNG FILTER(datatype(?XML_LNG) = euvoc:XML_LNG)
                """,
                "ISO_639_2B": """
                    ?concept skos:notation ?ISO_639_2B FILTER(datatype(?ISO_639_2B) = euvoc:ISO_639_2B)
                """,
            },
            prefixes={
                "euvoc": "http://publications.europa.eu/ontology/euvoc#",
            },
        )
        sparql_results["Languages (EU Publications)"] = count
    except Exception:
        log.exception("Failed to load Languages")
        sparql_results["Languages (EU Publications)"] = 0

    # File Types from EU Publications Office (download RDF and query locally)
    try:
        log.info("Loading File Types from EU Publications Office...")
        count = sparql_loader.load_from_sparql_endpoint(
            endpoint="http://publications.europa.eu/resource/authority/file-type",
            scheme_uri="http://publications.europa.eu/resource/authority/file-type",
            load_subgraphs=True,  # Load individual concept URIs for full label data
        )
        sparql_results["File Types (EU Publications)"] = count
    except Exception:
        log.exception("Failed to load File Types")
        sparql_results["File Types (EU Publications)"] = 0

    # Other sources loaded from RDF files
    rdf_sources = [
        # Access Rights from COAR
        {
            "name": "Access Rights (COAR)",
            "url": "https://vocabularies.coar-repositories.org/access_rights/access_rights.nt",
            "format": "nt",
            "extra_file": input_dir / "addon_access_rights.ttl",
        },
        # Resource Types from COAR
        {
            "name": "Resource Types (COAR)",
            "url": "https://vocabularies.coar-repositories.org/resource_types/resource_types.nt",
            "format": "nt",
        },
    ]

    for source_config in rdf_sources:
        source_name = source_config["name"]
        try:
            log.info("Loading %s...", source_name)

            # Load main vocabulary
            count = sparql_loader.load_from_url(
                source_config["url"],
                format=source_config["format"],
            )
            sparql_results[source_name] = count

            # Load extra file if specified
            if "extra_file" in source_config:
                extra_file = source_config["extra_file"]
                if extra_file.exists():
                    log.info("Loading extra data from %s...", extra_file.name)
                    extra_count = sparql_loader.load_from_file(
                        extra_file,
                        format="turtle",
                    )
                    log.info("Loaded %d additional triples from %s", extra_count, extra_file.name)
                else:
                    log.warning("Extra file not found: %s", extra_file)

        except Exception:
            log.exception("Failed to load %s", source_name)
            sparql_results[source_name] = 0

    log.info("SPARQL loading results:")
    for source_name, count in sparql_results.items():
        log.info("  - %s: %d triples", source_name, count)

    total_sparql_triples = sum(sparql_results.values())
    log.info("Total triples loaded from SPARQL sources: %d", total_sparql_triples)
    log.info("Triplestore now contains %d triples", store.size())

    # Step 4: Load SSSOM mapping files
    log.info("Step 4: Loading SSSOM mapping files")
    sssom_loader = SSSOMLoader(store)

    # Load all SSSOM files from the sssom directory
    if sssom_dir.exists():
        log.info("Loading SSSOM files from %s...", sssom_dir)
        sssom_results = sssom_loader.load_directory(sssom_dir, pattern="*.tsv")

        log.info("SSSOM loading results:")
        for filename, count in sorted(sssom_results.items()):
            log.info("  - %s: %d triples", filename, count)

        total_sssom_triples = sum(sssom_results.values())
        log.info("Total triples loaded from SSSOM files: %d", total_sssom_triples)
        log.info("Triplestore now contains %d triples", store.size())
    else:
        log.warning("SSSOM directory not found: %s", sssom_dir)
        total_sssom_triples = 0

    # Step 5: Create Invenio fixtures from the triplestore
    log.info("Step 5: Generating Invenio fixtures")
    generator = FixtureGenerator(store)
    fixture_results = generator.generate_all(output_dir)

    log.info("Fixture generation results:")
    for filename, count in sorted(fixture_results.items()):
        log.info("  - %s: %d items", filename, count)

    total_fixtures = sum(fixture_results.values())
    log.info("Total items written across all fixtures: %d", total_fixtures)

    # Step 6: Dump the triplestore to a Turtle file
    log.info("Step 6: Dumping triplestore to Turtle file")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "vocabularies.ttl"

    log.info("Writing triplestore to %s...", output_file)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(store.serialize(format="turtle"))
    log.info("Successfully wrote %d triples to %s", store.size(), output_file)

    # Print summary statistics
    if log_level in ("INFO", "DEBUG"):
        log.info("=" * 70)
        log.info("FINAL TRIPLESTORE SUMMARY")
        log.info("=" * 70)
        print_statistics(store)
        print_concept_schemes(store)
        log.info("=" * 70)

    log.info("Vocabulary conversion completed")
    log.info("Final triplestore size: %d triples", store.size())


if __name__ == "__main__":
    convert_vocabularies()

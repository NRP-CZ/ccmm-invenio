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
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS

from ccmm_invenio.conversion.csv_loader import CSVToRDFLoader
from ccmm_invenio.conversion.fixture_generator import FixtureGenerator
from ccmm_invenio.conversion.rdf_store import RDFTripleStore
from ccmm_invenio.conversion.sparql_loader import SPARQLLoader
from ccmm_invenio.conversion.sssom_loader import SSSOMLoader
from ccmm_invenio.conversion.utils import print_concept_schemes, print_statistics
from ccmm_invenio.conversion.yaml_loader import YAMLToRDFLoader

log = logging.getLogger(__name__)


def create_nma_vocabulary_terms(store: RDFTripleStore) -> None:
    """Create NMA vocabulary terms from external schemes.

    For each concept in external schemes, create a corresponding concept
    in our NMA scheme with all the same properties, plus skos:exactMatch
    linking back to the original.

    Args:
        store: The RDF triplestore containing external concepts

    """
    log.info("Creating NMA vocabulary terms from external schemes")

    # Define mappings from external schemes to NMA schemes
    scheme_mappings = [
        {
            "external_scheme": "http://publications.europa.eu/resource/authority/language",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/languages",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/languages/",
        },
        {
            "external_scheme": "http://publications.europa.eu/resource/authority/file-type",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/filetypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/filetypes/",
        },
        {
            "external_scheme": "http://purl.org/coar/access_right/scheme",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/accessrights",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/accessrights/",
        },
        {
            "external_scheme": "http://purl.org/coar/resource_type/scheme",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/resourcetypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/resourcetypes/",
        },
        {
            "external_scheme": "https://vocabs.ccmm.cz/registry/codelist/AgentRole/",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/resourceagentroletypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/resourceagentroletypes/",
        },
        {
            "external_scheme": "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/titletypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/titletypes/",
        },
        {
            "external_scheme": "https://vocabs.ccmm.cz/registry/codelist/LocationRelation/",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/locationrelationtypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/locationrelationtypes/",
        },
        {
            "external_scheme": "https://vocabs.ccmm.cz/registry/codelist/RelationType/",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/relationtypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/relationtypes/",
        },
        {
            "external_scheme": "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/subjectcategories",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/subjectcategories/",
        },
        {
            "external_scheme": "https://vocabs.ccmm.cz/registry/codelist/TimeReference/",
            "nma_scheme": "https://nma.eosc.cz/vocabularies/datetypes",
            "nma_base_uri": "https://nma.eosc.cz/vocabularies/datetypes/",
        },
    ]

    total_created = 0

    for mapping in scheme_mappings:
        external_scheme_uri = mapping["external_scheme"]
        nma_scheme_uri = mapping["nma_scheme"]
        nma_base_uri = mapping["nma_base_uri"]

        log.info("Creating NMA concepts from %s to %s", external_scheme_uri, nma_scheme_uri)

        # Query for all concepts in the external scheme
        query = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?concept
            WHERE {{
                ?concept a skos:Concept ;
                         skos:inScheme <{external_scheme_uri}> .
            }}
        """

        concepts = list(store.graph.query(query))

        if not concepts:
            log.info("No concepts found in %s, skipping", external_scheme_uri)
            continue

        log.info("Found %d concepts to transform", len(concepts))

        nma_graph = Graph()

        for row in concepts:
            external_concept_uri = row[0]
            external_concept_str = str(external_concept_uri)

            # Extract the identifier from the external URI, lowercased to match
            # the fixture generator's ID convention (e.g. .../language/CEN -> cen)
            concept_id = external_concept_str.rstrip("/").split("/")[-1].lower()

            # Create NMA concept URI
            nma_concept_uri = URIRef(f"{nma_base_uri}{concept_id}")

            # Add concept type and scheme
            nma_graph.add((nma_concept_uri, RDF.type, SKOS.Concept))
            nma_graph.add((nma_concept_uri, SKOS.inScheme, URIRef(nma_scheme_uri)))

            # Add exactMatch to original concept
            nma_graph.add((nma_concept_uri, SKOS.exactMatch, external_concept_uri))

            # Copy all other properties from the external concept
            # Get all predicates and objects for this concept
            for pred, obj in store.graph.predicate_objects(external_concept_uri):
                pred_str = str(pred)

                # Skip properties we've already handled or don't want to copy
                if pred_str in [
                    str(RDF.type),
                    str(SKOS.inScheme),
                ]:
                    continue

                # Copy the property to the NMA concept
                nma_graph.add((nma_concept_uri, pred, obj))

        # Merge NMA concepts into store
        before_count = store.size()
        store.merge(nma_graph)
        after_count = store.size()
        added = after_count - before_count

        log.info("Created %d NMA concepts with %d triples for %s", len(concepts), added, nma_scheme_uri)
        total_created += len(concepts)

    log.info("Total NMA concepts created: %d", total_created)


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
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching of downloaded RDF data",
)
def convert_vocabularies(
    input_dir: Path | None,
    sssom_dir: Path | None,
    output_dir: Path | None,
    log_level: str,
    no_cache: bool,
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

    use_cache = not no_cache

    log.info("Starting vocabulary conversion")
    log.info("Input directory: %s", input_dir)
    log.info("SSSOM directory: %s", sssom_dir)
    log.info("Output directory: %s", output_dir)
    log.info("Cache enabled: %s", use_cache)

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
    sparql_loader = SPARQLLoader(store, use_cache=use_cache)

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

    # Step 3.5: Load YAML vocabulary files (e.g., licenses)
    log.info("Step 3.5: Loading YAML vocabulary files")
    yaml_loader = YAMLToRDFLoader(store)
    yaml_results = {}

    # Load licenses
    licenses_file = input_dir / "licenses.yaml"
    if licenses_file.exists():
        try:
            log.info("Loading licenses from %s...", licenses_file)
            count = yaml_loader.load_yaml_file(
                licenses_file,
                concept_scheme="https://nma.eosc.cz/vocabularies/licenses",
                vocabulary_type="licenses",
            )
            yaml_results["Licenses"] = count
        except Exception:
            log.exception("Failed to load licenses")
            yaml_results["Licenses"] = 0
    else:
        log.warning("Licenses file not found: %s", licenses_file)
        yaml_results["Licenses"] = 0

    # Load subject schemes
    subject_schemes_file = input_dir / "subject_schemes.yaml"
    if subject_schemes_file.exists():
        try:
            log.info("Loading subject schemes from %s...", subject_schemes_file)
            count = yaml_loader.load_yaml_file(
                subject_schemes_file,
                concept_scheme="https://nma.eosc.cz/vocabularies/subjectschemes",
                vocabulary_type="subjectschemes",
            )
            yaml_results["Subject Schemes"] = count
        except Exception:
            log.exception("Failed to load subject schemes")
            yaml_results["Subject Schemes"] = 0
    else:
        log.warning("Subject schemes file not found: %s", subject_schemes_file)
        yaml_results["Subject Schemes"] = 0

    log.info("YAML loading results:")
    for source_name, count in yaml_results.items():
        log.info("  - %s: %d concepts", source_name, count)

    total_yaml_concepts = sum(yaml_results.values())
    log.info("Total concepts loaded from YAML files: %d", total_yaml_concepts)
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

    # Step 5: Create nma vocabulary terms
    log.info("Step 5: Creating NMA vocabulary terms")
    create_nma_vocabulary_terms(store)

    # Step 6: Create Invenio fixtures from the triplestore
    log.info("Step 6: Generating Invenio fixtures")
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

    log.info("Writing sorted triplestore to %s...", output_file)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(store.serialize_sorted(format="turtle"))
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

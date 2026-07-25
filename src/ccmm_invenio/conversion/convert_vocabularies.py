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
from typing import TYPE_CHECKING, Any, cast

import click
from rdflib import Literal, URIRef
from rdflib.namespace import SKOS, split_uri

from ccmm_invenio.conversion.csv_loader import CSVLoader
from ccmm_invenio.conversion.rdf_store import CCMM, CCMM_MISC, CCMM_PROPS, NMA, RDFTripleStore
from ccmm_invenio.conversion.sparql_loader import NetworkCache, NetworkRDFLoader, TurtleLoader
from ccmm_invenio.conversion.sssom_loader import SSSOMLoader
from ccmm_invenio.conversion.writer import GenericVocabularyWriter
from ccmm_invenio.conversion.yaml_loader import YAMLLoader

if TYPE_CHECKING:
    from collections.abc import Callable

    from ccmm_invenio.conversion.loader import VocabularyLoader


log = logging.getLogger(__name__)


class VocabularyConverter:
    """A vocabulary converter that manages the triplestore and conversion steps."""

    def __init__(self):
        """Initialize the VocabularyConverter with an empty triplestore."""
        self.store = RDFTripleStore()

    def load_vocabulary_to_triple_store(self, uri: str, loader: VocabularyLoader) -> int:
        """Load a vocabulary from the given URI using the specified loader and store it in the triplestore.

        Args:
            uri (str): The URI of the vocabulary to load.
            loader (VocabularyLoader): The loader to use for loading the vocabulary.

        Returns the number of concepts loaded.

        """
        return loader.load(uri, self.store)

    def add_identifiers(self) -> None:
        """Add DC identifiers to the triplestore."""
        log.info("Adding DC identifiers to the triplestore...")
        for subject in self.store.graph.subjects(SKOS.inScheme):
            self.store.graph.add((subject, NMA.original_iri, subject))
            nma_iri = self._convert_iri_to_nma_iri(str(subject))
            self.store.graph.add((subject, NMA.nma_iri, URIRef(nma_iri)))
            self.store.graph.add((subject, NMA.nma_identifier, Literal(nma_iri.rsplit("/", maxsplit=1)[-1])))

    def _convert_iri_to_nma_iri(self, iri: str) -> str:
        iri = iri.rstrip("/")

        def _lookup_base(base: str) -> str | None:
            """Look up the NMA base URI for a given CCMM base URI."""
            known_bases = {
                "http://publications.europa.eu/resource/authority/language": "https://nma.eosc.cz/vocabularies/languages",
                "http://publications.europa.eu/resource/authority/file-type": "https://nma.eosc.cz/vocabularies/filetypes",
                "http://purl.org/coar/access_right": "https://nma.eosc.cz/vocabularies/accessrights",
                "http://purl.org/coar/resource_type": "https://nma.eosc.cz/vocabularies/resourcetypes",
                "https://vocabs.ccmm.cz/registry/codelist/AgentRole": "https://nma.eosc.cz/vocabularies/resourceagentroletypes",
                "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle": "https://nma.eosc.cz/vocabularies/titletypes",
                "https://vocabs.ccmm.cz/registry/codelist/LocationRelation": "https://nma.eosc.cz/vocabularies/locationrelationtypes",
                "https://vocabs.ccmm.cz/registry/codelist/RelationType": "https://nma.eosc.cz/vocabularies/relationtypes",
                "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory": "https://nma.eosc.cz/vocabularies/subjects",
                "https://vocabs.ccmm.cz/registry/codelist/TimeReference": "https://nma.eosc.cz/vocabularies/datetypes",
                # "https://vocabs.ccmm.cz/registry/codelist/Subjects": "https://nma.eosc.cz/vocabularies/subjects",
                "https://cesnet.cz/licenses": "https://nma.eosc.cz/vocabularies/licenses",
                "https://cesnet.cz/subject-schemes": "https://nma.eosc.cz/vocabularies/subjectcategories",
                "https://cesnet.cz/identifier-schemes": "https://nma.eosc.cz/vocabularies/identifierschemes",
                "https://cesnet.cz/checksum-algorithms": "https://nma.eosc.cz/vocabularies/checksumalgorithms",
                "https://cesnet.cz/description-types": "https://nma.eosc.cz/vocabularies/descriptiontypes",
            }
            if base not in known_bases:
                return None
            return known_bases[base]

        base, identifier = iri.rsplit("/", maxsplit=1)
        identifier = identifier.lower()
        while base:
            nma_base = _lookup_base(base)
            if nma_base:
                return f"{nma_base}/{identifier}"
            if "/" not in base:
                break
            base, rest = base.rsplit("/", maxsplit=1)
            rest = rest.lower()
            identifier = f"{rest}/{identifier}"
        raise ValueError(f"Could not convert IRI {iri}")

    def _convert_skos_scheme_to_nma_scheme(self, scheme: str) -> URIRef:
        scheme_map = {
            "https://cesnet.cz/licenses": NMA.licenses,
            "https://cesnet.cz/subject-schemes": NMA.subjectcategories,
            "https://cesnet.cz/identifier-schemes": NMA.identifierschemes,
            "https://cesnet.cz/checksum-algorithms": NMA.checksumalgorithms,
            "https://cesnet.cz/description-types": NMA.descriptiontypes,
            "https://vocabs.ccmm.cz/registry/codelist/AgentRole/": NMA.resourceagentroletypes,
            "https://vocabs.ccmm.cz/registry/codelist/AlternateTitle/": NMA.titletypes,
            "https://vocabs.ccmm.cz/registry/codelist/LocationRelation/": NMA.locationrelationtypes,
            "https://vocabs.ccmm.cz/registry/codelist/RelationType/": NMA.relationtypes,
            "https://vocabs.ccmm.cz/registry/codelist/SubjectCategory/": NMA.subjects,
            "https://vocabs.ccmm.cz/registry/codelist/TimeReference/": NMA.datetypes,
            "http://purl.org/coar/access_right/scheme": NMA.accessrights,
            "http://purl.org/coar/resource_type/scheme": NMA.resourcetypes,
            "http://publications.europa.eu/resource/authority/language": NMA.languages,
            "http://publications.europa.eu/resource/authority/language/0001": NMA.languages,
            "http://publications.europa.eu/resource/authority/language/0002": NMA.languages,
            "http://publications.europa.eu/resource/authority/language/0003": NMA.languages,
            "http://publications.europa.eu/resource/authority/file-type": NMA.filetypes,
        }
        return scheme_map[str(scheme)]

    def add_nma_terms(self, predicate_map: dict[tuple[str | None, URIRef], URIRef | Callable]) -> str | None:
        """Add NMA terms to the triplestore as exact matches."""
        log.info("Adding NMA terms to the triplestore...")

        def lookup_predicate(subject: URIRef, predicate: URIRef, rdf_object: Any) -> tuple[URIRef | None, Any]:
            subject_scheme = str(subject).rsplit("/", maxsplit=1)[0]
            mapped_predicate = predicate_map.get((subject_scheme, predicate)) or predicate_map.get((None, predicate))
            if mapped_predicate is not None:
                if callable(mapped_predicate):
                    return mapped_predicate(subject, predicate, rdf_object)
                return mapped_predicate, rdf_object
            return None, None

        for subject, nma_subject in self.store.graph.subject_objects(NMA.nma_iri):
            self.store.graph.add((nma_subject, SKOS.exactMatch, subject))

            # for subject, get SKOS.inScheme and add it to the NMA subject
            for _, predicate, obj in self.store.graph.triples((subject, SKOS.inScheme, None)):
                # we need to remap the scheme to nma scheme: _convert_iri_to_nma_iri(self, iri: str)
                nma_scheme = self._convert_skos_scheme_to_nma_scheme(str(obj))
                self.store.graph.add((nma_subject, predicate, URIRef(nma_scheme)))

            # copy all triples from the original subject to the NMA subject
            for _, predicate, obj in self.store.graph.triples((subject, None, None)):
                self.store.graph.add((nma_subject, predicate, obj))
                mapped_predicate, mapped_obj = lookup_predicate(cast("URIRef", subject), cast("URIRef", predicate), obj)
                if mapped_predicate is not None:
                    self.store.graph.add((nma_subject, mapped_predicate, mapped_obj))

                if predicate == SKOS.notation:
                    # convert notation like skos:notation "CS"^^euvoc:EUDOR_LNG, "CS"^^euvoc:FD_060, "cs"^^euvoc:ISO_639_1
                    # to CCMM_PROPS.EUDOR_LNG -> "CS", CCMM_PROPS.FD_060 -> "CS", CCMM_PROPS.ISO_639_1 -> "cs"
                    datatype = getattr(obj, "datatype", None)
                    if datatype is not None:
                        prop_name = str(datatype).rsplit("#", maxsplit=1)[-1].rsplit("/", maxsplit=1)[-1]
                        self.store.graph.add((nma_subject, CCMM_PROPS[prop_name], Literal(str(obj))))

            # Copy inverse relationships: if something points TO the subject, make it point TO the NMA subject too
            # This handles cases like: lindat_concept skos:exactMatch original_subject
            # Which should become: lindat_concept skos:exactMatch nma_subject
            for subj, predicate, _ in self.store.graph.triples((None, None, subject)):
                # Skip if this would create a self-reference (subj == nma_subject)
                if subj == nma_subject:
                    continue
                # Also skip if the predicate is nma_iri or original_iri to avoid duplicating internal mappings
                if predicate in (NMA.nma_iri, NMA.original_iri):
                    continue
                # Add the same triple but with nma_subject as the object
                self.store.graph.add((subj, predicate, nma_subject))

    def extract_contributors_roles(self) -> None:
        """Extract contributors roles from the triplestore and store them in the triplestore in a different scheme."""
        for subject in self.store.graph.subjects(SKOS.inScheme, NMA.resourceagentroletypes):
            if not str(subject).startswith(f"{NMA.resourceagentroletypes}/contributor"):
                continue
            subject_id = split_uri(str(subject))[-1]
            nma_subject = URIRef(f"{NMA.contributorsroles}/{subject_id}")
            # add inScheme
            self.store.graph.add((nma_subject, SKOS.inScheme, NMA.contributorsroles))
            # remove inScheme resourceagentroletypes
            self.store.graph.remove((subject, SKOS.inScheme, NMA.resourceagentroletypes))

            for predicate, obj in self.store.graph.predicate_objects(subject):
                self.store.graph.add((nma_subject, predicate, obj))

    def mark_subjects(self) -> None:
        """Mark subjects vocabulary terms with frascati."""
        for subject in self.store.graph.subjects(SKOS.inScheme, URIRef(f"{CCMM.SubjectCategory}/")):
            self.store.graph.add((subject, CCMM_MISC.scheme, Literal("frascati")))

            # get the prefLabel in english of the subject
            pref_label = next(
                (
                    label
                    for label in self.store.graph.objects(subject, SKOS.prefLabel)
                    if label.language == "en"
                ),
                None,
            )

            if pref_label is not None:
                self.store.graph.add((subject, CCMM_MISC.subject, pref_label))

def load_vocabularies(converter: VocabularyConverter, input_dir: Path) -> None:
    """Load vocabularies from the input directory and store them in the triplestore."""
    cache = NetworkCache(Path.cwd() / ".cache")

    licenses_file = input_dir / "licenses.yaml"
    log.info("Loading licenses from %s...", licenses_file)
    converter.load_vocabulary_to_triple_store(
        str(licenses_file), YAMLLoader(concept_scheme="https://cesnet.cz/licenses")
    )

    subject_schemes_file = input_dir / "subject_schemes.yaml"
    log.info("Loading subject schemes from %s...", subject_schemes_file)
    converter.load_vocabulary_to_triple_store(
        str(subject_schemes_file), YAMLLoader(concept_scheme="https://cesnet.cz/subject-schemes")
    )

    identifier_schemes_file = input_dir / "identifier_schemes.yaml"
    log.info("Loading subject schemes from %s...", identifier_schemes_file)
    converter.load_vocabulary_to_triple_store(
        str(identifier_schemes_file), YAMLLoader(concept_scheme="https://cesnet.cz/identifier-schemes")
    )

    checksum_algorithms_file = input_dir / "checksum_algorithms.yaml"
    log.info("Loading checksum algorithms from %s...", checksum_algorithms_file)
    converter.load_vocabulary_to_triple_store(
        str(checksum_algorithms_file), YAMLLoader(concept_scheme="https://cesnet.cz/checksum-algorithms")
    )

    description_types_file = input_dir / "description_types.yaml"
    log.info("Loading description types from %s...", description_types_file)
    converter.load_vocabulary_to_triple_store(
        str(description_types_file), YAMLLoader(concept_scheme="https://cesnet.cz/description-types")
    )

    for f in input_dir.rglob("*.csv"):
        log.info("Loading %s...", f)
        converter.load_vocabulary_to_triple_store(str(f), CSVLoader())

    for f in input_dir.rglob("*.ttl"):
        log.info("Loading %s...", f)
        converter.load_vocabulary_to_triple_store(str(f), TurtleLoader())

    for source_url in [
        "https://vocabularies.coar-repositories.org/access_rights/access_rights.nt",
        "https://vocabularies.coar-repositories.org/resource_types/resource_types.nt",
    ]:
        log.info("Loading %s...", source_url)
        converter.load_vocabulary_to_triple_store(source_url, NetworkRDFLoader(cache))

    converter.load_vocabulary_to_triple_store(
        "http://publications.europa.eu/resource/authority/language",
        NetworkRDFLoader(cache, serialization_format="xml", load_subgraphs=True),
    )

    converter.load_vocabulary_to_triple_store(
        "http://publications.europa.eu/resource/authority/file-type",
        NetworkRDFLoader(cache, serialization_format="xml", load_subgraphs=True),
    )

    for f in input_dir.rglob("*.tsv"):
        log.info("Loading vocabulary mapping file %s...", f)
        converter.load_vocabulary_to_triple_store(str(f), SSSOMLoader())

    log.info("Loaded %d triples", converter.store.size())


def is_primary_language(store: RDFTripleStore, subject: URIRef) -> bool:
    """Check if the subject is a primary language (it has a two-letter ISO code) in the triplestore."""
    return any(store.graph.triples((subject, CCMM_PROPS.ISO_639_1, None)))


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

    converter = VocabularyConverter()
    load_vocabularies(converter, input_dir)

    converter.add_identifiers()
    converter.mark_subjects()
    converter.add_nma_terms(
        {
            # convert original_iri to exactMatch
            (None, NMA.original_iri): SKOS.exactMatch,
        }
    )
    converter.extract_contributors_roles()

    store = converter.store

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "vocabularies.ttl"

    log.info("Writing sorted triplestore to %s...", output_file)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(store.serialize_sorted(format="turtle"))
    log.info("Successfully wrote %d triples to %s", store.size(), output_file)

    GenericVocabularyWriter(store).write(output_dir / "ccmm_access_rights.yaml", NMA.accessrights)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_agent_roles.yaml", NMA.resourceagentroletypes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_alternate_title_types.yaml", NMA.titletypes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_contributor_types.yaml", NMA.contributorsroles)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_file_types.yaml", NMA.filetypes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_languages_all.yaml", NMA.languages)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_languages_primary.yaml", NMA.languages, is_primary_language)

    GenericVocabularyWriter(store).write(output_dir / "ccmm_licenses.yaml", NMA.licenses)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_location_relation_types.yaml", NMA.locationrelationtypes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_rdm_subjects.yaml", NMA.subjects, output_hierarchy=False)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_relation_types.yaml", NMA.relationtypes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_resource_types.yaml", NMA.resourcetypes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_subject_categories.yaml", NMA.subjectcategories)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_identifier_schemes.yaml", NMA.identifierschemes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_checksum_algorithms.yaml", NMA.checksumalgorithms)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_description_types.yaml", NMA.descriptiontypes)
    # GenericVocabularyWriter(store).write(output_dir / "ccmm_subject_schemes.yaml", NMA.subjectschemes)
    GenericVocabularyWriter(store).write(output_dir / "ccmm_time_reference_types.yaml", NMA.datetypes)


if __name__ == "__main__":
    convert_vocabularies()

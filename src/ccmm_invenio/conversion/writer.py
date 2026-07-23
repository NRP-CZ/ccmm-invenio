import logging
from collections.abc import Callable
from itertools import groupby
from pathlib import Path
from typing import Any, override

import yaml
from rdflib import SKOS, URIRef
from rdflib.namespace import split_uri

from ccmm_invenio.conversion.rdf_store import CCMM_MISC, CCMM_PROPS, NMA, RDFTripleStore

log = logging.getLogger(__name__)


class VocabularyWriter:
    """Base class for writing vocabulary data to a file."""

    def __init__(self, store: RDFTripleStore):
        self.store = store

    def write(self, output_file: Path, namespace: URIRef) -> None:
        """Write the vocabulary data to the output file."""

    def select_concepts(self, namespace: URIRef) -> list[tuple[URIRef, list[tuple[URIRef, Any]]]]:
        """Select the concepts to write to the output file."""
        # select all concepts in the namespace that have a skos:inScheme property with the given namespace
        # return the list of concepts together with all their properties, ordered by the concept uri
        query = f"""
        SELECT ?concept ?property ?value
        WHERE {{
            ?concept skos:inScheme <{namespace}> .
            ?concept ?property ?value .
        }}
        ORDER BY ?concept
        """
        results = self.store.query(query)
        return [
            (concept, [(row[1], row[2]) for row in properties])
            for concept, properties in groupby(results, key=lambda row: row[0])
        ]


class GenericVocabularyWriter(VocabularyWriter):
    """Generic vocabulary writer that writes the vocabulary data to a file."""

    @override
    def write(
        self,
        output_file: Path,
        namespace: URIRef,
        filter_func: Callable[[RDFTripleStore, URIRef], bool] | None = None,
    ) -> None:
        """Write the vocabulary data to the output file."""
        log.info("Writing namespace %s to %s", namespace, output_file)
        records = []
        for concept, properties in self.select_concepts(namespace):
            if filter_func and not filter_func(self.store, concept):
                continue
            converted_record: dict[str, Any] = {"props": {}, "identifiers": []}
            converted_record["props"]["iri"] = str(concept)
            converted_record["identifiers"].append({"identifier": str(concept), "scheme": str(NMA)})
            for prop, value in properties:
                if prop == SKOS.prefLabel:
                    converted_record.setdefault("title", {})[value.language] = str(value)
                elif prop == SKOS.definition:
                    converted_record.setdefault("description", {})[value.language] = str(value)
                elif prop == SKOS.exactMatch:
                    converted_record["identifiers"].append({"identifier": str(value), "scheme": split_uri(value)[0]})
                elif prop == NMA.nma_identifier:
                    converted_record["id"] = str(value)
                elif prop in CCMM_PROPS:
                    converted_record.setdefault("props", {})[split_uri(prop)[1]] = str(value)
                elif prop == CCMM_MISC.icon:
                    converted_record["icon"] = str(value)
                elif prop == CCMM_MISC.tag:
                    converted_record.setdefault("tags", []).append(str(value))
            if "title" not in converted_record:
                continue

            # we need an English fallback, so use the first available language if 'en' is not present
            # and pretend it is the English
            if "en" not in converted_record["title"]:
                converted_record["title"]["en"] = next(iter(converted_record["title"].values()))

            records.append(converted_record)

        if len(records) == 0:
            raise ValueError("No records found for namespace %s", namespace)

        with output_file.open("w") as f:
            yaml.safe_dump(records, f, allow_unicode=True)
        log.info("Wrote %d records to %s", len(records), output_file)

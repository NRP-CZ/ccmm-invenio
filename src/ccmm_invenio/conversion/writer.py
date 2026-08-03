import logging
from collections.abc import Callable
from graphlib import TopologicalSorter
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

    def identifier_entry(self, value: URIRef) -> dict[str, str]:
        """Build an {identifier, scheme} entry for the given identifier URI.

        The scheme is resolved from the identifier's own skos:inScheme assertions
        (falling back to splitting the URI itself when it has none). A URI can
        belong to several concept schemes at once (e.g. a general authority table
        and a specific versioned one); schemes that are themselves a more specific
        variant of another candidate (i.e. start with it) are dropped, and among
        what remains we pick the one the identifier's URI actually falls under.
        """
        candidates = list(self.store.graph.objects(value, SKOS.inScheme))
        if not candidates:
            return {"identifier": str(value), "scheme": split_uri(str(value))[0]}

        candidates = [
            candidate
            for candidate in candidates
            if not any(
                candidate != other and str(candidate).startswith(str(other)) for other in candidates
            )
        ]

        # a single candidate is authoritative regardless of whether it happens to be
        # a URL-prefix of the identifier (skos:inScheme is not required to be one)
        if len(candidates) == 1:
            return {"identifier": str(value), "scheme": str(candidates[0])}

        matching = [candidate for candidate in candidates if str(value).startswith(str(candidate))]
        if len(matching) != 1:
            msg = (
                f"Could not unambiguously resolve a scheme for identifier {value} "
                f"among candidates {candidates} (matching: {matching})"
            )
            raise ValueError(msg)
        return {"identifier": str(value), "scheme": str(matching[0])}

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
        output_hierarchy: bool = True,
    ) -> None:
        """Write the vocabulary data to the output file."""
        log.info("Writing namespace %s to %s", namespace, output_file)
        records = []
        output_ids: set[str] = set()

        # First, collect all concepts with their broader relationships
        # Map child_id -> parent_id (using just the ID part, not full URIs)
        hierarchy_map: dict[str, str] = {}
        for concept, properties in self.select_concepts(namespace):
            concept_id = concept.rsplit("/", maxsplit=1)[-1]
            for prop, _value in properties:
                if prop == SKOS.broader:
                    parent_id = str(_value).rsplit("/", maxsplit=1)[-1]
                    hierarchy_map[concept_id] = parent_id

        # First pass: collect all IDs that will be in the output
        for concept, properties in self.select_concepts(namespace):
            if filter_func and not filter_func(self.store, concept):
                continue
            # Check if concept has a title (required field)
            has_title = False
            for prop, _value in properties:
                if prop == SKOS.prefLabel:
                    has_title = True
                    break
            if has_title:
                concept_id = str(concept).rsplit("/", maxsplit=1)[-1]
                output_ids.add(concept_id)

        # Second pass: build records
        for concept, properties in self.select_concepts(namespace):
            if filter_func and not filter_func(self.store, concept):
                continue
            converted_record: dict[str, Any] = {"props": {}, "identifiers": [], "crosswalks": []}
            converted_record["props"]["iri"] = str(concept)
            converted_record["identifiers"].append({"identifier": str(concept), "scheme": str(NMA)})

            # Add identifiers from SKOS.exactMatch where concept is the subject
            # (this concept IS equivalent to these other URIs)
            for prop, value in properties:
                if prop == SKOS.prefLabel:
                    if len(value.language) != 2:
                        log.warning(
                            "Language tag '%s' is not a two-character code, can not be used in invenio",
                            value.language,
                        )
                    else:
                        converted_record.setdefault("title", {})[value.language] = str(value)
                elif prop == SKOS.definition:
                    if len(value.language) != 2:
                        log.warning(
                            "Language tag '%s' is not a two-character code, can not be used in invenio",
                            value.language,
                        )
                    else:
                        converted_record.setdefault("description", {})[value.language] = str(value)
                elif prop == SKOS.exactMatch:
                    converted_record["identifiers"].append(self.identifier_entry(value))
                elif prop == NMA.nma_identifier:
                    converted_record["id"] = str(value)
                elif prop in CCMM_PROPS:
                    converted_record.setdefault("props", {})[split_uri(prop)[1]] = str(value)
                elif prop == CCMM_MISC.icon:
                    converted_record["icon"] = str(value)
                elif prop == CCMM_MISC.tag:
                    converted_record.setdefault("tags", []).append(str(value))
                elif prop == CCMM_MISC.scheme:
                    converted_record["scheme"] = str(value)
                elif prop == CCMM_MISC.subject:
                    converted_record["subject"] = str(value)

            # Add mappings from SKOS.exactMatch where concept is the object
            # (other vocabularies map their concepts TO this one)
            for subj, _, _ in self.store.graph.triples((None, SKOS.exactMatch, concept)):
                # Skip self-references (when the subject is the same as the current concept)
                if subj == concept:
                    continue
                converted_record["crosswalks"].append(self.identifier_entry(subj))
            if "title" not in converted_record:
                continue
            if not converted_record["crosswalks"]:
                del converted_record["crosswalks"]
            if not converted_record["identifiers"]:
                del converted_record["identifiers"]
            # we need an English fallback, so use the first available language if 'en' is not present
            # and pretend it is the English
            if "en" not in converted_record["title"]:
                converted_record["title"]["en"] = next(iter(converted_record["title"].values()))

            # Add hierarchy information if this concept has a parent AND the parent is in the output
            concept_id = str(concept).rsplit("/", maxsplit=1)[-1]
            if concept_id in hierarchy_map and output_hierarchy:
                parent_id = hierarchy_map[concept_id]
                if parent_id in output_ids:
                    converted_record["hierarchy"] = {"parent": parent_id}

            records.append(converted_record)

        if len(records) == 0:
            raise ValueError("No records found for namespace %s", namespace)

        records.sort(key=lambda r: r["props"]["iri"])

        # Perform topological sort to ensure parents come before children
        # Build dependency graph: each child depends on its parent
        record_by_id: dict[str, dict[str, Any]] = {r["props"]["iri"].rsplit("/", maxsplit=1)[-1]: r for r in records}

        # Build graph for TopologicalSorter: node -> dependencies (parents must come before children)
        graph: dict[str, tuple[str, ...]] = {}
        for record in records:
            record_id = record["id"]
            deps = []
            if "hierarchy" in record:
                parent_id = record["hierarchy"]["parent"]
                if parent_id in record_by_id:  # Only consider parents that are in output
                    deps.append(parent_id)
            graph[record_id] = tuple(deps)

        # Use TopologicalSorter with alphabetical tiebreaker
        # TopologicalSorter.get_ready() returns nodes with no pending dependencies
        ts = TopologicalSorter(graph)
        ts.prepare()

        sorted_records: list[dict[str, Any]] = []

        while ts.is_active():
            # Get all currently ready nodes
            ready = list(ts.get_ready())
            if not ready:
                break  # Cycle detected

            # Sort alphabetically and process one at a time
            ready.sort()
            for current_id in ready:
                sorted_records.append(record_by_id[current_id])
                ts.done(current_id)

        records = sorted_records

        with output_file.open("w") as f:
            yaml.safe_dump(records, f, allow_unicode=True)
        log.info("Wrote %d records to %s", len(records), output_file)

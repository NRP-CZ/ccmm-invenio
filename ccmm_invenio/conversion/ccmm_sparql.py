import logging
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Any, Callable, cast
from urllib.error import HTTPError, URLError

from rdflib import SKOS, Graph, URIRef
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm.contrib.concurrent import process_map

from .base import VocabularyReader

# Set up logging to see retry attempts
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom retry configuration
RETRY_CONFIG: dict[str, Any] = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, min=2, max=30),  # 2s, 4s, 8s, etc. up to 30s
    "retry": retry_if_exception_type((URLError, HTTPError, ConnectionError)),
    "before_sleep": before_sleep_log(logger, logging.WARNING),
    "reraise": True,
}


@retry(**RETRY_CONFIG)
def parse_source(url: str, format: str = "xml") -> Graph:
    """Parse RDF with automatic retries for transient errors."""
    g = Graph()
    try:
        g.parse(url, format=format)
        return g
    except Exception as e:
        logger.warning(f"Attempt failed for {url}: {str(e)}")
        raise  # Re-raise for tenacity to handle


def join_with_commas(prop: str, parent: dict[str, Any]) -> None:
    parent[prop] = ", ".join(sorted(parent[prop]))


class SPARQLReader(VocabularyReader):
    """Download rdf locally, enrich it and call sparql to convert the RDF to Invenio YAML format."""

    def __init__(
        self,
        name: str,
        endpoint: str,
        skos_concept: str,
        extra: Path | None = None,  # turtle serialization of extra triples
        load_subgraphs: bool = True,
        format: str = "xml",
        extra_props: dict[str, str] | None = None,
        prefixes: dict[str, str] | None = None,
        array_resolution: Callable[[str, dict[str, Any]], None] = join_with_commas,
    ):
        """Initialize the SPARQL reader.

        :param name: Name of the vocabulary.
        :param endpoint: SPARQL endpoint URL.
        :param skos_concept: SKOS concept scheme URI.
        :param extra: Path to a turtle file with extra triples.
        :param load_subgraphs: Whether to load subgraphs.
        :param format: Format of the SPARQL file at the endpoint.
        :param extra_props: Additional properties to include in the results.
                            Keys are the names of the properties,
                            and values is the sparql query to get the value,
                            will be wrapped in an OPTIONAL clause.
        :param prefixes: Prefixes to use in the SPARQL query.
        :param array_resolution: Function to resolve array properties (default is to join with commas).
        """
        super().__init__(name)
        self.endpoint = endpoint
        self.skos_concept = skos_concept
        self.extra = extra
        self.load_subgraphs = load_subgraphs
        self.format = format
        self.extra_props = extra_props or {}
        self.prefixes = prefixes or {}
        self.array_resolution = array_resolution

    def data(self) -> list[dict[str, str]]:
        """Convert CCMM from SPARQL to YAML that can be imported to NRP Invenio."""

        # whole_graph: Graph = parse_source("file:///tmp/ccmm.ttl", format="turtle")
        whole_graph: Graph = parse_source(self.endpoint, format=self.format)

        if self.load_subgraphs:
            self._load_subgraphs(whole_graph)

        # add extra triples to the graph
        if self.extra:
            extra_graph = Graph()
            with open(self.extra, "r", encoding="utf-8") as extra_file:
                extra_graph.parse(extra_file, format="turtle")
            whole_graph += extra_graph

        # # save the whole graph to a turtle file /tmp/ccmm.ttl
        # whole_graph.serialize("/tmp/ccmm.ttl", format="turtle")

        query = """
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    {{prefixes}}

    SELECT ?concept ?label_cs ?label_en ?description_cs ?description_en ?identifier ?broader {{extra_props}}
    WHERE {
    ?concept a skos:Concept ;
                skos:inScheme ?scheme .

    # Get English label (prefLabel first, then altLabel)
    OPTIONAL {
        { ?concept skos:prefLabel ?prefLabel_en FILTER(lang(?prefLabel_en) = "en") }
        UNION
        { ?concept skos:altLabel ?altLabel_en }
        BIND(COALESCE(?prefLabel_en, ?altLabel_en) AS ?label_en)
    }
    
    # Get Czech label (prefLabel first, then english label)
    OPTIONAL {
        { ?concept skos:prefLabel ?label_cs FILTER(lang(?label_cs) = "cs") }
    }

    # Get English description (skos:definition)
    OPTIONAL {
        { ?concept skos:definition ?description_en FILTER(lang(?description_en) = "en") }
    }
    
    # Get Czech description (skos:definition)
    OPTIONAL {
        { ?concept skos:definition ?description_cs FILTER(lang(?description_cs) = "cs") }
    }

    # Get dc:identifier if available
    OPTIONAL { ?concept dc:identifier ?identifier }

    # Get skos:broader if available
    OPTIONAL { ?concept skos:broader ?broader }

    # Get extra properties
    {{extra_props_sparql}}

    }
    
    ORDER BY ?concept                                            
                        """

        query = query.replace(
            "{{prefixes}}",
            "\n".join(
                f"PREFIX {key}: <{value}>" for key, value in self.prefixes.items()
            ),
        )
        query = query.replace(
            "{{extra_props}}",
            " ".join(f"?{key}" for key in self.extra_props),
        )
        query = query.replace(
            "{{extra_props_sparql}}",
            "\n".join(f"OPTIONAL {{ {value} }}" for value in self.extra_props.values()),
        )
        rows = whole_graph.query(
            query,
            initBindings={
                "scheme": URIRef(self.skos_concept),
            },
        )
        converted: dict[str, Any] = {}
        by_iri: dict[str, str] = {}
        for row in cast(tuple[Any, ...], rows):
            row = [str(x) if x is not None else None for x in row]
            (
                iri,
                title_cs,
                title_en,
                description_cs,
                description_en,
                term_id,
                broader,
                *row_props,
            ) = row
            # Skip empty rows
            if not iri:
                continue
            # Skip rows without titles
            if title_cs is None and title_en is None:
                continue

            # set term_id if it was not provided
            if not term_id:
                term_id = iri.strip("/").split("/")[-1]
                term_id = term_id.strip("#").split("#")[-1]

            if term_id not in converted:
                term: dict[str, Any] = {"id": term_id}
                term["props"] = defaultdict(set[str])
                term["title"] = {}
                term["description"] = {}
                converted[term_id] = term
            else:
                term = converted[term_id]

            if "cs" not in term["title"]:
                term["title"]["cs"] = title_cs or title_en
            if "en" not in term["title"]:
                term["title"]["en"] = title_en or title_cs
            if "iri" not in term["props"]:
                term["props"]["iri"] = {iri}
            if "cs" not in term["description"] and description_cs:
                term["description"]["cs"] = description_cs
            if "en" not in term["description"] and description_en:
                term["description"]["en"] = description_en

            for prop, value in zip(self.extra_props.keys(), row_props):
                if value is not None:
                    term["props"][prop].add(str(value))

            if broader:
                term["hierarchy"] = {"parent": broader}

            by_iri[iri] = term_id

        # Resolve the hierarchy
        for term in converted.values():
            if "hierarchy" in term:
                parent = term["hierarchy"]["parent"]
                term["hierarchy"]["parent"] = by_iri[parent]

        # Convert sets to comma-separated strings
        for term in converted.values():
            term["props"] = dict(term["props"])
            for prop in list(term["props"]):
                self.array_resolution(prop, term["props"])

        to_sort = [dict(term) for term in converted.values()]

        ret_ids: set[str] = set()
        ret: list[dict[str, Any]] = []

        remaining: list[dict[str, Any]] = []
        for term in to_sort:
            # if there is no parent, add the term
            if "hierarchy" not in term:
                ret.append(term)
                ret_ids.add(term["id"])
                continue
            else:
                remaining.append(term)

        while remaining:
            to_sort = remaining
            remaining = []

            for term in to_sort:
                parent = term["hierarchy"]["parent"]
                if parent in ret_ids:
                    ret.append(term)
                    ret_ids.add(term["id"])
                else:
                    remaining.append(term)
            if len(to_sort) == len(remaining):
                raise ValueError(
                    f"There is a cycle in the hierarchy, please check the data: {remaining}"
                )

        return ret

    def _load_subgraphs(self, whole_graph: Graph) -> None:
        """Load all subgraphs from the SKOS concept scheme and merge them into the whole graph."""

        # Get all concepts
        scheme = URIRef(self.skos_concept)
        subjects = [str(x) for x in whole_graph.subjects(SKOS.inScheme, scheme)]

        # enrich graph with all the subjects
        for subject_graph in process_map(
            partial(parse_source, format=self.format),
            subjects,
            max_workers=20,
            chunksize=10,
            leave=False,
            unit="subgraph",
        ):
            whole_graph += cast(Graph, subject_graph)

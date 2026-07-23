#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Load vocabulary data from SPARQL endpoints into RDF triplestore."""

from __future__ import annotations

import logging
import re
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast, override
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rdflib import SKOS, Graph
from tenacity import (  # type: ignore[reportMissingImports]
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm.contrib.concurrent import process_map  # type: ignore[reportMissingImports]

from .loader import VocabularyLoader

if TYPE_CHECKING:
    from ccmm_invenio.conversion.rdf_store import RDFTripleStore

log = logging.getLogger(__name__)


class TurtleLoader(VocabularyLoader):
    """Loads Turtle RDF files from a URI into an RDF triple store."""

    @override
    def load(self, uri: str, store: RDFTripleStore) -> int:
        log.info("Loading Turtle RDF from %s", uri)

        file_path = Path(uri)

        if not file_path.exists():
            log.error("File not found: %s", file_path)
            return 0

        try:
            graph = Graph()
            with file_path.open(encoding="utf-8") as f:
                graph.parse(f, format="turtle")

            store.merge(graph)

            log.info("Loaded %d triples from %s", len(graph), file_path.name)
        except Exception:
            log.exception("Failed to load RDF from file: %s", file_path)
        # we do not know how many concepts were loaded, so returning 0
        return 0


# Retry configuration for network requests
RETRY_CONFIG = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, min=2, max=30),
    "retry": retry_if_exception_type((URLError, HTTPError, ConnectionError)),
    "before_sleep": before_sleep_log(log, logging.WARNING),
    "reraise": True,
}


class NetworkCache:
    """Manages caching of network requests."""

    def __init__(self, cache_dir: Path):
        """Initialize the NetworkCache with a cache directory."""
        self.cache_dir = cache_dir / "network_rdf_loader"

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a given cache key.

        Args:
            cache_key: The SHA256 cache key

        Returns:
            Path to the cache file

        """
        without_proto = re.split("://", cache_key)[-1]
        return self.cache_dir / f"{without_proto}.cache"

    def _load_from_cache(self, cache_path: Path) -> bytes | None:
        """Load RDF graph from cache file if it exists.

        Args:
            cache_path: Path to the cache file

        Returns:
            The cached data as bytes, or None if the cache does not exist

        """
        if not cache_path.exists():
            return None

        return cache_path.read_bytes()

    def _save_to_cache(self, cache_path: Path, data: bytes) -> None:
        """Save bytes to cache file.

        Args:
            data: The data to save
            cache_path: Path to save the cache file

        """
        # Ensure cache directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        log.debug("Saving to cache: %s", cache_path)
        cache_path.write_bytes(data)

    @retry(**RETRY_CONFIG)
    def fetch_url(self, url: str) -> bytes:
        """Fetch the content of a URL and return it as bytes."""
        cache_path = self._get_cache_path(url)
        data = self._load_from_cache(cache_path)
        if data is not None:
            return data

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError(f"Invalid URL, expecting http:// or https://, got: {url}")
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
        resp = urlopen(req)  # noqa: S310

        if resp.status != 200:
            raise HTTPError(url, resp.status, resp.reason, resp.headers, None)
        data = resp.read()

        self._save_to_cache(cache_path, data)
        return data

    def load_rdf_graph(self, uri: str, serialization_format: str = "nt") -> Graph:
        """Load an RDF graph from a URI using the specified format."""
        data = self.fetch_url(uri)
        graph = Graph()
        graph.parse(data=data, format=serialization_format)
        return graph


class NetworkRDFLoader(VocabularyLoader):
    """Loads NT RDF files from a URI into an RDF triple store."""

    def __init__(self, cache: NetworkCache, serialization_format: str = "nt", load_subgraphs: bool = False) -> None:
        """Initialize the NTLoader with a network cache."""
        super().__init__()
        self.cache = cache
        self.serialization_format = serialization_format
        self.load_subgraphs = load_subgraphs

    @override
    def load(self, uri: str, store: RDFTripleStore) -> int:
        graph = self.cache.load_rdf_graph(uri, serialization_format=self.serialization_format)
        if self.load_subgraphs:
            self._load_subgraphs(graph, serialization_format=self.serialization_format)
        store.merge(graph)
        return len(graph)

    def _load_subgraphs(self, graph: Graph, serialization_format: str = "xml") -> None:
        """Load all subgraphs from the SKOS concept scheme and merge them into the graph.

        This downloads each individual concept URI to get full details (labels, etc.).

        Args:
            graph: Graph to enrich with subgraph data
            serialization_format: RDF format to use when fetching subgraphs

        """
        log.info("Loading subgraphs for concepts...")

        # Get all concepts that belong to any scheme
        subjects = [str(x) for x in graph.subjects(SKOS.inScheme)]
        log.info("Found %d concepts to load subgraphs for", len(subjects))

        # Load all subgraphs in parallel using partial to bind the format and use_cache parameters
        for subject_graph in process_map(
            partial(self.cache.load_rdf_graph, serialization_format=serialization_format),
            subjects,
            max_workers=20,
            chunksize=10,
            leave=False,
            unit="subgraph",
            desc="Loading subgraphs",
        ):
            graph += cast("Graph", subject_graph)

        log.info("Finished loading subgraphs, graph now has %d triples", len(graph))

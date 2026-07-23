from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rdf_store import RDFTripleStore


class VocabularyLoader:
    """A base class for loading RDF vocabularies into a triplestore."""

    def load(self, uri: str, store: RDFTripleStore) -> int:
        """Load the vocabulary from the given URI into the triplestore.

        Returns:
            The number of concepts loaded

        """
        raise NotImplementedError

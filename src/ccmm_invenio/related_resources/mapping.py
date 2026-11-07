# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""The base of the resolver metadata mappings."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from flask import current_app
from oarepo_related_resources.resolvers.base import ResolverProblem, ResolverProblemLevel


class ResolverMapping(ABC):
    """Map the metadata of one resolved identifier to CCMM record metadata.

    The ``resolve_*`` methods of a subclass fill parts of `processed_metadata`; decorated with
    ``oarepo_related_resources.resolvers.utils.handle_errors`` a failing one is logged and skipped, so one bad
    value does not lose the whole record. Values that can not be mapped are reported with `_add_problem`.
    """

    provider: str
    """Name the problems are reported under (the resolver name in oarepo-related-resources)."""

    def __init__(self, metadata: Any):
        """Create the mapping of the resolver's ``metadata`` (what its ``get_metadata`` returns)."""
        self.metadata = metadata
        self.processed_metadata: dict[str, Any] = {}
        self.problems: list[ResolverProblem] = []

    def _add_problem(
        self,
        message: Any,
        *,
        level: ResolverProblemLevel = ResolverProblemLevel.WARNING,
        exc: Exception | None = None,
    ) -> None:
        """Report a value that could not be mapped."""
        problem = ResolverProblem(resolver=self.provider, message=str(message), level=level, original_exception=exc)
        self.problems.append(problem)
        if level == ResolverProblemLevel.ERROR:
            current_app.logger.error("%s mapping problem: %s", self.provider, problem.message, exc_info=exc)

    @abstractmethod
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Map the whole metadata, return the record metadata and the problems."""
        raise NotImplementedError

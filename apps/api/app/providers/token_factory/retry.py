from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from ...errors import FailureCategory, InfrastructureError

T = TypeVar("T")

_RETRYABLE_CATEGORIES = frozenset(
    {
        FailureCategory.PROVIDER_UNAVAILABLE,
        FailureCategory.REQUEST_TIMEOUT,
        FailureCategory.RATE_LIMIT,
    }
)


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential-backoff retry policy for transient provider failures."""

    max_attempts: int
    backoff_factor: float
    base_delay_seconds: float = 0.5

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    async def execute(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Run `fn`, retying transient failures until attempts are exhausted."""
        attempt = 0
        while True:
            attempt += 1
            try:
                return await fn()
            except InfrastructureError as exc:
                if attempt >= self.max_attempts or not self._is_retryable(exc):
                    raise
                delay = self.base_delay_seconds * (self.backoff_factor ** (attempt - 1))
                await asyncio.sleep(delay)

    @staticmethod
    def _is_retryable(exc: InfrastructureError) -> bool:
        return exc.category in _RETRYABLE_CATEGORIES

from abc import ABC, abstractmethod


class Limiter(ABC):
    """Common interface implemented by every rate-limiting algorithm here."""

    @abstractmethod
    def allow(self, n: int = 1) -> bool:
        """Return True if n requests may proceed right now."""
        raise NotImplementedError

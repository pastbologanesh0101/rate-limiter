class FakeClock:
    """A manually-advanced clock so tests don't depend on wall time."""

    def __init__(self, start: float = 0.0):
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds

from abc import ABC, abstractmethod
from collections.abc import Callable

from app.schemas import MatchResultsResponse, RawTrajectoriesData


class PipelineContext:
    """Context passed to pipelines to allow throttled progress reporting."""
    def __init__(self, callback: Callable[[int, str], None] | None = None):
        self.callback = callback
        self._last_pct: int = -1

    def report(self, pct: int, message: str = "") -> None:
        pct = max(0, min(100, int(pct)))
        if self.callback and pct != self._last_pct:
            self._last_pct = pct
            self.callback(pct, message)


class BasePipeline(ABC):
    """Abstract base class for match analytics pipelines (Mock & Real)."""

    @abstractmethod
    def run(
        self,
        video_path: str | None,
        match_id: str,
        ctx: PipelineContext,
        video_meta: dict | None = None
    ) -> tuple[MatchResultsResponse, RawTrajectoriesData]:
        """Runs the pipeline and returns (results, raw_trajectories)."""

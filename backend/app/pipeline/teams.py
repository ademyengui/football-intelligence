from collections import Counter

import numpy as np


class TeamClassifier:
    """Notebook-compatible SigLIP/UMAP/KMeans team classifier."""

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = None
        self.fitted = False

    def fit(self, crops: list[np.ndarray]) -> None:
        if not crops:
            raise ValueError("No player crops were collected for team classification")
        from sports.common.team import TeamClassifier as SportsTeamClassifier

        self.model = SportsTeamClassifier(device=self.device)
        self.model.fit(crops)
        self.fitted = True

    def predict(self, crops: list[np.ndarray]) -> np.ndarray:
        if not self.fitted:
            raise ValueError("TeamClassifier must be fitted before prediction")
        if not crops:
            return np.empty((0,), dtype=int)
        return np.asarray(self.model.predict(crops), dtype=int)

    def classify_tracks(self, color_vectors, track_stats):
        """Compatibility path for the existing unit seam; video processing uses fit/predict."""
        eligible = [
            tid for tid, stats in track_stats.items()
            if stats.get("majority_class") == "player"
            and stats.get("duration_s", 0.0) >= 5.0
            and stats.get("player_ratio", 0.0) >= 0.8
            and color_vectors.get(tid)
        ]
        if len(eligible) < 2:
            return {
                tid: (None, "other", stats.get("majority_class", "unknown"))
                for tid, stats in track_stats.items()
            }
        vectors = np.asarray([np.median(color_vectors[tid], axis=0) for tid in eligible])
        first = vectors[0]
        distances = np.linalg.norm(vectors - first, axis=1)
        second = vectors[int(np.argmax(distances))]
        results = {}
        for tid, stats in track_stats.items():
            if stats.get("majority_class") == "goalkeeper":
                results[tid] = (None, "other", "goalkeeper")
                continue
            vector = np.median(color_vectors.get(tid, [first]), axis=0)
            team = "A" if np.linalg.norm(vector - first) <= np.linalg.norm(vector - second) else "B"
            results[tid] = (team, "outfield", "player")
        return results

    @staticmethod
    def majority_team(team_ids: np.ndarray) -> int | None:
        if len(team_ids) == 0:
            return None
        return int(Counter(team_ids.tolist()).most_common(1)[0][0])

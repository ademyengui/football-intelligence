import cv2
import numpy as np
from sklearn.cluster import KMeans

class TeamClassifier:
    """
    Lab colour-based team & role classifier.
    Extracts upper-body crops, filters grass pixels, fits KMeans(k=2) on eligible tracks.
    """

    def extract_upper_body_color(self, frame_bgr: np.ndarray, bbox: tuple[float, float, float, float]) -> np.ndarray | None:
        """Extracts median Lab color vector from upper body crop excluding grass pixels."""
        x1, y1, x2, y2 = bbox
        h, w = frame_bgr.shape[:2]

        x1_c = max(0, int(x1))
        y1_c = max(0, int(y1))
        x2_c = min(w, int(x2))
        y2_c = min(h, int(y2))

        bw = x2_c - x1_c
        bh = y2_c - y1_c
        if bw < 5 or bh < 5:
            return None

        # Upper body crop: 15% to 55% height, central 60% width
        crop_y1 = int(y1_c + 0.15 * bh)
        crop_y2 = int(y1_c + 0.55 * bh)
        crop_x1 = int(x1_c + 0.20 * bw)
        crop_x2 = int(x1_c + 0.80 * bw)

        if crop_y2 <= crop_y1 or crop_x2 <= crop_x1:
            return None

        crop_bgr = frame_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
        if crop_bgr.size == 0:
            return None

        # Convert to HSV to detect grass
        crop_hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
        # Grass HSV mask: Hue 35-85, Saturation > 60
        grass_mask = (crop_hsv[:, :, 0] >= 35) & (crop_hsv[:, :, 0] <= 85) & (crop_hsv[:, :, 1] > 60)
        non_grass_mask = ~grass_mask

        crop_lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
        valid_pixels = crop_lab[non_grass_mask]

        if len(valid_pixels) < 10:
            # Fallback to all pixels in crop if non-grass pixels are too few
            valid_pixels = crop_lab.reshape(-1, 3)

        median_color = np.median(valid_pixels, axis=0)
        return median_color.astype(np.float32)

    def classify_tracks(
        self,
        track_color_vectors: dict[int, list[np.ndarray]],
        track_stats: dict[int, dict]
    ) -> dict[int, tuple[str | None, str, str]]:
        """
        Classifies tracks into (team, role, detector_hint).
        Returns dict: track_id -> (team "A"|"B"|None, role "outfield"|"other", detector_hint).
        """
        results: dict[int, tuple[str | None, str, str]] = {}

        track_medians: dict[int, np.ndarray] = {}
        for tid, colors in track_color_vectors.items():
            if colors:
                track_medians[tid] = np.median(np.array(colors), axis=0)

        # Identify eligible tracks for KMeans fit
        eligible_tids = []
        eligible_colors = []

        for tid, stats in track_stats.items():
            duration = stats.get('duration_s', 0.0)
            player_ratio = stats.get('player_ratio', 0.0)
            majority_class = stats.get('majority_class', 'unknown')

            if majority_class in ('goalkeeper', 'referee'):
                results[tid] = (None, "other", majority_class)
            elif duration >= 5.0 and player_ratio >= 0.8 and tid in track_medians:
                eligible_tids.append(tid)
                eligible_colors.append(track_medians[tid])
            else:
                results[tid] = (None, "other", majority_class if majority_class != "player" else "unknown")

        if len(eligible_colors) >= 2:
            colors_arr = np.array(eligible_colors)
            kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
            labels = kmeans.fit_predict(colors_arr)

            # Assign cluster with more tracks to Team A
            count_0 = np.sum(labels == 0)
            count_1 = np.sum(labels == 1)

            team_0 = "A" if count_0 >= count_1 else "B"
            team_1 = "B" if team_0 == "A" else "A"

            cluster_map = {0: team_0, 1: team_1}

            # Compute median within-cluster distance
            dists_0 = np.linalg.norm(colors_arr[labels == 0] - kmeans.cluster_centers_[0], axis=1) if count_0 > 0 else np.array([1.0])
            dists_1 = np.linalg.norm(colors_arr[labels == 1] - kmeans.cluster_centers_[1], axis=1) if count_1 > 0 else np.array([1.0])
            median_dist = float(np.median(np.concatenate([dists_0, dists_1])))

            threshold = 2.5 * max(median_dist, 5.0)

            # Classify ALL tracks based on centroids
            for tid, color_vec in track_medians.items():
                if tid in results and results[tid][1] == "other" and results[tid][2] in ('goalkeeper', 'referee'):
                    continue

                d0 = np.linalg.norm(color_vec - kmeans.cluster_centers_[0])
                d1 = np.linalg.norm(color_vec - kmeans.cluster_centers_[1])

                if d0 > threshold and d1 > threshold:
                    results[tid] = (None, "other", "unknown")
                else:
                    assigned_cluster = 0 if d0 <= d1 else 1
                    team = cluster_map[assigned_cluster]
                    results[tid] = (team, "outfield", "player")

        else:
            # Fallback if insufficient eligible tracks for KMeans fit
            for tid in track_stats.keys():
                if tid not in results:
                    results[tid] = (None, "other", "unknown")

        return results

import cv2
import numpy as np


class NaiveCalibrator:
    def __init__(self, pitch_width_m: float = 105.0, pitch_height_m: float = 68.0):
        self.pitch_width_m = pitch_width_m
        self.pitch_height_m = pitch_height_m

    def get_foot_point_px(self, bbox):
        x1, y1, x2, y2 = bbox
        return (x1 + x2) / 2.0, float(y2)

    def pixel_to_pitch(self, foot_px, frame_size):
        foot_x, foot_y = foot_px
        frame_w, frame_h = frame_size
        return round((foot_x / frame_w) * self.pitch_width_m, 1), round((foot_y / frame_h) * self.pitch_height_m, 1)


class HomographyCalibrator:
    """Notebook ViewTransformer equivalent with meter and native pitch coordinates."""

    def __init__(self, confidence_threshold: float = 0.5, min_points: int = 4):
        from sports.configs.soccer import SoccerPitchConfiguration

        self.config = SoccerPitchConfiguration()
        self.confidence_threshold = confidence_threshold
        self.min_points = min_points
        self.matrix = None

    def get_foot_point_px(self, bbox):
        x1, y1, x2, y2 = bbox
        return (x1 + x2) / 2.0, float(y2)

    def update(self, frame_points, confidences) -> bool:
        frame_points = np.asarray(frame_points, dtype=np.float32)
        confidences = np.asarray(confidences, dtype=np.float32)
        mask = confidences > self.confidence_threshold
        if int(np.count_nonzero(mask)) < self.min_points:
            return False
        source = frame_points[mask]
        target = np.asarray(self.config.vertices, dtype=np.float32)[mask]
        matrix, _ = cv2.findHomography(source, target, method=0)
        if matrix is None or not np.isfinite(matrix).all():
            return False
        self.matrix = matrix
        return True

    def pixel_to_pitch_native(self, point_px) -> tuple[float, float]:
        if self.matrix is None:
            raise ValueError("Pitch calibration is unavailable: no reliable field keypoints detected")
        point = np.asarray([[point_px]], dtype=np.float32)
        projected = cv2.perspectiveTransform(point, self.matrix)[0, 0]
        return float(projected[0]), float(projected[1])

    def pixel_to_pitch(self, point_px) -> tuple[float, float]:
        x, y = self.pixel_to_pitch_native(point_px)
        return round(float(np.clip(x / self.config.length * 105.0, 0.0, 105.0)), 1), round(
            float(np.clip(y / self.config.width * 68.0, 0.0, 68.0)), 1
        )

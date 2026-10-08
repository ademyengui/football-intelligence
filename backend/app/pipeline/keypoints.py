import importlib.util

import numpy as np

from app.config import settings


class FieldKeypointDetector:
    """Lazy Roboflow pitch-keypoint model adapter."""

    def __init__(self):
        self.device = "cpu"
        if importlib.util.find_spec("torch") is not None:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.model_id = settings.ROBOFLOW_FIELD_MODEL_ID
        print(f"[FieldKeypointDetector] Using compute device: {self.device}")

    def load_model(self):
        if self.model is None:
            from inference import get_model

            if not settings.ROBOFLOW_API_KEY:
                raise ValueError("ROBOFLOW_API_KEY is required for real pipeline processing")
            self.model = get_model(model_id=self.model_id, api_key=settings.ROBOFLOW_API_KEY)
            print(f"[FieldKeypointDetector] Loaded Roboflow model '{self.model_id}'")

    def infer_frame(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        self.load_model()
        import supervision as sv

        results = self.model.infer(frame_bgr, confidence=settings.DETECTION_CONFIDENCE)
        if not results:
            return np.empty((0, 2), dtype=np.float32), np.empty((0,), dtype=np.float32)

        key_points = sv.KeyPoints.from_inference(results[0])
        if key_points.xy is None or len(key_points.xy) == 0:
            return np.empty((0, 2), dtype=np.float32), np.empty((0,), dtype=np.float32)

        xy = np.asarray(key_points.xy[0], dtype=np.float32)
        confidence = np.asarray(key_points.confidence[0], dtype=np.float32)
        return xy, confidence

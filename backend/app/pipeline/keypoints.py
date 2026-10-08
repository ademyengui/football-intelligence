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
        self.model_id = "/".join(settings.ROBOFLOW_FIELD_MODEL_ID.split("/")[-2:])
        print(f"[FieldKeypointDetector] Using compute device: {self.device}")

    def load_model(self):
        if self.model is None:
            from inference_sdk import InferenceHTTPClient

            if not settings.ROBOFLOW_API_KEY:
                raise ValueError("ROBOFLOW_API_KEY is required for real pipeline processing")
            self.model = InferenceHTTPClient.init(
                api_url="https://serverless.roboflow.com",
                api_key=settings.ROBOFLOW_API_KEY,
            )
            print(f"[FieldKeypointDetector] Connected to Roboflow model '{self.model_id}'")

    def infer_frame(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        self.load_model()
        results = self.model.infer(
            frame_bgr,
            model_id=self.model_id,
        )
        predictions = results.get("predictions", []) if isinstance(results, dict) else []
        if not predictions:
            return np.empty((0, 2), dtype=np.float32), np.empty((0,), dtype=np.float32)

        keypoints = predictions[0].get("keypoints", [])
        if not keypoints:
            return np.empty((0, 2), dtype=np.float32), np.empty((0,), dtype=np.float32)
        xy = np.zeros((32, 2), dtype=np.float32)
        confidence = np.zeros((32,), dtype=np.float32)
        for point in keypoints:
            index = int(point.get("class_id", -1))
            if 0 <= index < len(xy):
                xy[index] = (point["x"], point["y"])
                confidence[index] = point.get("confidence", predictions[0]["confidence"])
        return xy, confidence

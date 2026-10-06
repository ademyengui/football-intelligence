import torch
from app.config import settings

class Detector:
    """
    Wrapper for Roboflow inference model.
    Detects ball, goalkeeper, player, referee classes.
    """
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Detector] Initialized detector on device: {self.device}")
        self.model = None

    def load_model(self):
        if self.model is None:
            try:
                from inference import get_model
                model_id = settings.ROBOFLOW_MODEL_ID
                api_key = settings.ROBOFLOW_API_KEY
                self.model = get_model(model_id=model_id, api_key=api_key)
                print(f"[Detector] Loaded Roboflow model '{model_id}' on {self.device}")
            except Exception as e:
                print(f"[Detector] Failed to load Roboflow model: {e}")
                raise e

    def infer_frame(self, frame_bgr) -> tuple[list[dict], dict | None]:
        """
        Runs inference on a single BGR frame.
        Returns (non_ball_detections, best_ball_detection).
        non_ball_detections: list of dicts {'bbox': [x1, y1, x2, y2], 'confidence': float, 'class_id': int, 'class_name': str}
        """
        if self.model is None:
            self.load_model()

        results = self.model.infer(frame_bgr, confidence=settings.DETECTION_CONFIDENCE)

        non_ball_dets = []
        best_ball_det = None
        best_ball_conf = -1.0

        if results and len(results) > 0:
            predictions = getattr(results[0], 'predictions', []) or []
            for pred in predictions:
                x = pred.x
                y = pred.y
                w = pred.width
                h = pred.height
                conf = pred.confidence
                class_name = str(pred.class_name).lower()

                x1 = x - w / 2.0
                y1 = y - h / 2.0
                x2 = x + w / 2.0
                y2 = y + h / 2.0

                # Map class name to ID (ball=0, goalkeeper=1, player=2, referee=3)
                if 'ball' in class_name:
                    cid = 0
                    if conf > best_ball_conf:
                        best_ball_conf = conf
                        best_ball_det = {
                            'bbox': [x1, y1, x2, y2],
                            'confidence': float(conf),
                            'center': (x, y)
                        }
                elif 'keeper' in class_name or 'goalkeeper' in class_name:
                    cid = 1
                    non_ball_dets.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(conf),
                        'class_id': cid,
                        'class_name': 'goalkeeper'
                    })
                elif 'referee' in class_name:
                    cid = 3
                    non_ball_dets.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(conf),
                        'class_id': cid,
                        'class_name': 'referee'
                    })
                else:  # player
                    cid = 2
                    non_ball_dets.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(conf),
                        'class_id': cid,
                        'class_name': 'player'
                    })

        return non_ball_dets, best_ball_det


class NaiveCalibrator:
    """
    NaiveCalibrator: Linear mapping from pixel coordinates to 105m x 68m pitch space.
    Foot point = midpoint of bottom edge of bounding box: ((x1 + x2)/2, y2).
    """
    def __init__(self, pitch_width_m: float = 105.0, pitch_height_m: float = 68.0):
        self.pitch_width_m = pitch_width_m
        self.pitch_height_m = pitch_height_m

    def get_foot_point_px(self, bbox: list[float] | tuple[float, float, float, float]) -> tuple[float, float]:
        """Calculates foot point (midpoint of bottom edge) from bounding box [x1, y1, x2, y2]."""
        x1, y1, x2, y2 = bbox
        foot_x = (x1 + x2) / 2.0
        foot_y = float(y2)
        return foot_x, foot_y

    def pixel_to_pitch(self, foot_px: tuple[float, float], frame_size: tuple[int, int]) -> tuple[float, float]:
        """Maps pixel (x, y) on a frame of size (frame_w, frame_h) to pitch metres (x_m, y_m)."""
        foot_x, foot_y = foot_px
        frame_w, frame_h = frame_size

        if frame_w <= 0 or frame_h <= 0:
            return 0.0, 0.0

        x_m = (foot_x / float(frame_w)) * self.pitch_width_m
        y_m = (foot_y / float(frame_h)) * self.pitch_height_m

        # Clip to pitch boundaries
        x_m = max(0.0, min(self.pitch_width_m, x_m))
        y_m = max(0.0, min(self.pitch_height_m, y_m))

        return round(x_m, 1), round(y_m, 1)

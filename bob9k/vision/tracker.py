from __future__ import annotations

from bob9k.vision.models import TrackedTarget


class VisionTracker:
    def __init__(self, config: dict | None = None):
        self.apply_config(config or {})

    def apply_config(self, config: dict | None) -> None:
        config = config or {}
        self.pan_gain = float(config.get('pan_gain', 0.05))
        self.tilt_gain = float(config.get('tilt_gain', 0.05))
        self.x_deadzone_px = int(config.get('x_deadzone_px', 64))
        self.y_deadzone_px = int(config.get('y_deadzone_px', 48))
        self.smoothing_alpha = float(config.get('smoothing_alpha', 0.4))

    def choose_target(self, detections):
        if not detections:
            return None
        return max(detections, key=lambda det: det.area)

    def update(self, detections, frame_w: int, frame_h: int, current_pan: float, current_tilt: float):
        target = self.choose_target(detections)
        if not target:
            return TrackedTarget(detection=None, acquired=False), None, None

        frame_center_x = frame_w / 2.0
        frame_center_y = frame_h / 2.0
        error_x = float(target.center_x - frame_center_x)
        error_y = float(target.center_y - frame_center_y)

        adjusted_error_x = 0.0 if abs(error_x) < self.x_deadzone_px else error_x
        adjusted_error_y = 0.0 if abs(error_y) < self.y_deadzone_px else error_y

        target_pan = float(current_pan) + (adjusted_error_x * self.pan_gain)
        target_tilt = float(current_tilt) + (adjusted_error_y * self.tilt_gain)

        alpha = max(0.0, min(1.0, self.smoothing_alpha))
        next_pan = (alpha * target_pan) + ((1.0 - alpha) * float(current_pan))
        next_tilt = (alpha * target_tilt) + ((1.0 - alpha) * float(current_tilt))

        tracked = TrackedTarget(
            detection=target,
            error_x=error_x,
            error_y=error_y,
            acquired=True,
            lost_age_s=0.0,
        )
        return tracked, next_pan, next_tilt

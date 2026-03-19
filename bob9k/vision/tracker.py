from __future__ import annotations


class VisionTracker:
    def __init__(self, config: dict | None = None):
        self.apply_config(config or {})

    def apply_config(self, config: dict | None) -> None:
        config = config or {}
        self.pan_gain = float(config.get('pan_gain', 0.06))
        self.tilt_gain = float(config.get('tilt_gain', 0.06))
        self.x_deadzone_px = int(config.get('x_deadzone_px', 48))
        self.y_deadzone_px = int(config.get('y_deadzone_px', 36))
        self.smoothing_alpha = float(config.get('smoothing_alpha', 0.4))
        self.invert_error_x = bool(config.get('invert_error_x', False))
        self.invert_error_y = bool(config.get('invert_error_y', False))
        self.preferred_target = str(config.get('preferred_target', 'largest')).strip().lower()
        self.target_label = str(config.get('target_label', '') or '').strip().lower()
        self.min_target_area = int(config.get('min_target_area', 0))

    def _distance_from_center(self, det, frame_w: int, frame_h: int) -> float:
        dx = det.center_x - (frame_w / 2.0)
        dy = det.center_y - (frame_h / 2.0)
        return (dx * dx) + (dy * dy)

    def choose_target(self, detections, frame_w: int, frame_h: int):
        if not detections:
            return None
        candidates = [d for d in detections if getattr(d, 'area', 0) >= self.min_target_area]
        if not candidates:
            return None
        if self.target_label:
            labeled = [d for d in candidates if str(getattr(d, 'label', '')).lower() == self.target_label]
            if labeled:
                candidates = labeled
        preferred = self.preferred_target
        if preferred == 'center':
            return min(candidates, key=lambda d: self._distance_from_center(d, frame_w, frame_h))
        if preferred == 'highest_confidence':
            return max(candidates, key=lambda d: (getattr(d, 'confidence', 0.0), getattr(d, 'area', 0)))
        return max(candidates, key=lambda d: (getattr(d, 'area', 0), getattr(d, 'confidence', 0.0)))

    def move_to_target(self, target, frame_w: int, frame_h: int, current_pan: float, current_tilt: float):
        if not target:
            return None, None
        err_x = float(target.center_x - (frame_w / 2.0))
        err_y = float(target.center_y - (frame_h / 2.0))
        if self.invert_error_x:
            err_x = -err_x
        if self.invert_error_y:
            err_y = -err_y
        adj_x = 0.0 if abs(err_x) < self.x_deadzone_px else err_x
        adj_y = 0.0 if abs(err_y) < self.y_deadzone_px else err_y
        target_pan = float(current_pan) + (adj_x * self.pan_gain)
        target_tilt = float(current_tilt) + (adj_y * self.tilt_gain)
        alpha = max(0.0, min(1.0, self.smoothing_alpha))
        next_pan = (alpha * target_pan) + ((1.0 - alpha) * float(current_pan))
        next_tilt = (alpha * target_tilt) + ((1.0 - alpha) * float(current_tilt))
        return next_pan, next_tilt

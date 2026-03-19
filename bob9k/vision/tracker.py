from __future__ import annotations

from bob9k.vision.models import Detection, TrackedTarget


def _iou(a: Detection, b: Detection) -> float:
    ax1, ay1, ax2, ay2 = a.x, a.y, a.x + a.w, a.y + a.h
    bx1, by1, bx2, by2 = b.x, b.y, b.x + b.w, b.y + b.h
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = max(1, a.w * a.h + b.w * b.h - inter)
    return inter / union


class VisionTracker:
    def __init__(self, config: dict | None = None):
        self.current_target: Detection | None = None
        self.lock_frames = 0
        self.last_switch_reason: str | None = None
        self.apply_config(config or {})

    def apply_config(self, config: dict | None) -> None:
        config = config or {}
        self.pan_gain = float(config.get('pan_gain', 0.05))
        self.tilt_gain = float(config.get('tilt_gain', 0.05))
        self.x_deadzone_px = int(config.get('x_deadzone_px', 64))
        self.y_deadzone_px = int(config.get('y_deadzone_px', 48))
        self.smoothing_alpha = float(config.get('smoothing_alpha', 0.4))
        self.lock_hysteresis = bool(config.get('lock_hysteresis', True))
        self.lock_iou_threshold = float(config.get('lock_iou_threshold', 0.35))
        self.switch_margin = float(config.get('switch_margin', 0.15))
        self.min_lock_frames = int(config.get('min_lock_frames', 3))
        self.max_servo_step = float(config.get('max_servo_step', 4.0))

    def score_candidate(self, det: Detection, frame_w: int, frame_h: int) -> float:
        frame_area = max(1.0, float(frame_w * frame_h))
        area_ratio = float(det.area) / frame_area
        center_dx = abs(det.center_x - (frame_w / 2.0)) / max(1.0, frame_w / 2.0)
        center_dy = abs(det.center_y - (frame_h / 2.0)) / max(1.0, frame_h / 2.0)
        center_penalty = (center_dx + center_dy) * 0.5
        return (area_ratio * 2.0) + float(det.confidence) - center_penalty

    def choose_target(self, detections, frame_w: int, frame_h: int):
        if not detections:
            self.current_target = None
            self.lock_frames = 0
            self.last_switch_reason = 'no_detections'
            return None, False, self.last_switch_reason

        scored = sorted(detections, key=lambda det: self.score_candidate(det, frame_w, frame_h), reverse=True)
        best = scored[0]

        if not self.lock_hysteresis or self.current_target is None:
            switched = self.current_target is not None and self.current_target != best
            self.current_target = best
            self.lock_frames = 1 if not switched else 0
            self.last_switch_reason = 'new_target' if switched else 'best_candidate'
            return best, self.lock_frames >= self.min_lock_frames, self.last_switch_reason

        current = self.current_target
        current_score = self.score_candidate(current, frame_w, frame_h)
        best_score = self.score_candidate(best, frame_w, frame_h)
        overlap = _iou(current, best)
        current_still_present = any(_iou(current, cand) >= self.lock_iou_threshold for cand in detections)

        if current_still_present:
            matched = max(detections, key=lambda cand: _iou(current, cand))
            self.current_target = matched
            self.lock_frames += 1
            self.last_switch_reason = 'lock_hold'
            if best is not matched and best_score > (current_score + self.switch_margin):
                self.current_target = best
                self.lock_frames = 0
                self.last_switch_reason = 'better_candidate'
            return self.current_target, self.lock_frames >= self.min_lock_frames, self.last_switch_reason

        self.current_target = best
        self.lock_frames = 0 if overlap < self.lock_iou_threshold else 1
        self.last_switch_reason = 'reacquire'
        return best, self.lock_frames >= self.min_lock_frames, self.last_switch_reason

    def _clamp_step(self, current: float, target: float) -> float:
        delta = target - current
        if abs(delta) <= self.max_servo_step:
            return target
        return current + (self.max_servo_step if delta > 0 else -self.max_servo_step)

    def update(self, detections, frame_w: int, frame_h: int, current_pan: float, current_tilt: float):
        target, locked, switch_reason = self.choose_target(detections, frame_w, frame_h)
        if not target:
            return TrackedTarget(detection=None, acquired=False, locked=False, lock_frames=0, switch_reason=switch_reason, candidate_count=0), None, None

        frame_center_x = frame_w / 2.0
        frame_center_y = frame_h / 2.0
        error_x = float(target.center_x - frame_center_x)
        error_y = float(target.center_y - frame_center_y)

        adjusted_error_x = 0.0 if abs(error_x) < self.x_deadzone_px else error_x
        adjusted_error_y = 0.0 if abs(error_y) < self.y_deadzone_px else error_y

        target_pan = float(current_pan) + (adjusted_error_x * self.pan_gain)
        target_tilt = float(current_tilt) + (adjusted_error_y * self.tilt_gain)

        alpha = max(0.0, min(1.0, self.smoothing_alpha))
        smoothed_pan = (alpha * target_pan) + ((1.0 - alpha) * float(current_pan))
        smoothed_tilt = (alpha * target_tilt) + ((1.0 - alpha) * float(current_tilt))
        next_pan = self._clamp_step(float(current_pan), smoothed_pan)
        next_tilt = self._clamp_step(float(current_tilt), smoothed_tilt)

        tracked = TrackedTarget(
            detection=target,
            error_x=error_x,
            error_y=error_y,
            acquired=True,
            lost_age_s=0.0,
            locked=locked,
            lock_frames=self.lock_frames,
            switch_reason=switch_reason,
            candidate_count=len(detections),
        )
        return tracked, next_pan, next_tilt

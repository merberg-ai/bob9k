from __future__ import annotations

import threading
import time
from typing import Any

from bob9k.config import load_runtime_config, save_runtime_config
from bob9k.vision.detectors.haar_face import HaarFaceDetector
from bob9k.vision.detectors.haar_body import HaarBodyDetector
from bob9k.vision.detectors.motion import MotionDetector
from bob9k.vision.tracker import VisionTracker


def get_detector(name: str):
    if name == 'haar_face':
        return HaarFaceDetector()
    elif name == 'haar_body':
        return HaarBodyDetector()
    elif name == 'motion':
        return MotionDetector()
    return None


class TrackingService:
    DEFAULT_CONFIG = {
        'enabled': False,
        'mode': 'camera_track',
        'detector': 'haar_face',
        'target_label': 'face',
        'pan_gain': 0.05,
        'tilt_gain': 0.05,
        'x_deadzone_px': 64,
        'y_deadzone_px': 48,
        'smoothing_alpha': 0.4,
        'scan_when_lost': False,
        'lost_timeout_s': 2.0,
        'target_distance_cm': 30.0,
        'distance_tolerance_cm': 5.0,
        'confidence_threshold': 0.45,
        'min_detection_area': 0.01,
        'min_target_area': 0.02,
        'edge_reject_margin_px': 12,
        'detect_only_mode': False,
        'diagnostics_overlay': True,
        'lock_hysteresis': True,
        'lock_iou_threshold': 0.35,
        'switch_margin': 0.15,
        'min_lock_frames': 3,
        'process_every_n_frames': 1,
        'max_servo_step': 4,
        'servo_rate_limit_hz': 15,
    }

    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._thread = None
        self._stop_event = threading.Event()
        self._last_target_seen_ts: float | None = None
        self._last_servo_write_ts = 0.0
        self._frame_counter = 0

        try:
            import cv2  # noqa: F401
            import numpy as np  # noqa: F401
            self._cv_available = True
        except ImportError:
            self._cv_available = False

        self._tracking_config = self._build_tracking_config(self.runtime.config.get('tracking', {}))
        self.detector = get_detector(self._tracking_config.get('detector', 'haar_face')) if self._cv_available else None
        self.tracker = VisionTracker(self._tracking_config)
        self.target_distance_cm = float(self._tracking_config.get('target_distance_cm', 30.0))
        self.distance_tolerance_cm = float(self._tracking_config.get('distance_tolerance_cm', 5.0))

        self.runtime.state.tracking_mode = str(self._tracking_config.get('mode', 'camera_track'))
        self.runtime.state.tracking_detector = str(self._tracking_config.get('detector', 'haar_face'))
        self.runtime.state.tracking_enabled = bool(self._tracking_config.get('enabled', False))
        self.runtime.state.tracking_target_acquired = False
        self.runtime.state.tracking_disable_reason = None
        self.runtime.state.tracking_detect_only_mode = bool(self._tracking_config.get('detect_only_mode', False))
        self._update_detector_status()

    def _build_tracking_config(self, overrides: dict[str, Any] | None) -> dict[str, Any]:
        cfg = dict(self.DEFAULT_CONFIG)
        if overrides:
            cfg.update(overrides)
        return self._normalize_tracking_config(cfg)[0]

    def _normalize_tracking_config(self, source: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
        source = source or {}
        cfg = dict(self.DEFAULT_CONFIG)
        warnings: list[str] = []

        def _as_float(name: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
            raw = source.get(name, default)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                warnings.append(f'{name} value {raw!r} is invalid, using {default!r}.')
                value = float(default)
            if minimum is not None:
                value = max(minimum, value)
            if maximum is not None:
                value = min(maximum, value)
            return value

        def _as_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
            raw = source.get(name, default)
            try:
                value = int(raw)
            except (TypeError, ValueError):
                warnings.append(f'{name} value {raw!r} is invalid, using {default!r}.')
                value = int(default)
            if minimum is not None:
                value = max(minimum, value)
            if maximum is not None:
                value = min(maximum, value)
            return value

        cfg['enabled'] = bool(source.get('enabled', cfg['enabled']))
        cfg['detect_only_mode'] = bool(source.get('detect_only_mode', cfg['detect_only_mode']))
        cfg['diagnostics_overlay'] = bool(source.get('diagnostics_overlay', cfg['diagnostics_overlay']))
        cfg['lock_hysteresis'] = bool(source.get('lock_hysteresis', cfg['lock_hysteresis']))

        mode = str(source.get('mode', cfg['mode'])).strip().lower()
        if mode not in {'off', 'camera_track'}:
            warnings.append(f'mode value {mode!r} is unsupported, using {cfg["mode"]!r}.')
            mode = cfg['mode']
        cfg['mode'] = mode

        detector = str(source.get('detector', cfg['detector'])).strip().lower()
        if detector not in {'haar_face', 'haar_body', 'motion'}:
            warnings.append(f'detector value {detector!r} is unsupported, using {cfg["detector"]!r}.')
            detector = cfg['detector']
        cfg['detector'] = detector

        cfg['target_label'] = str(source.get('target_label', cfg['target_label'])).strip().lower() or 'face'
        cfg['pan_gain'] = _as_float('pan_gain', float(cfg['pan_gain']), 0.0, 1.0)
        cfg['tilt_gain'] = _as_float('tilt_gain', float(cfg['tilt_gain']), 0.0, 1.0)
        cfg['x_deadzone_px'] = _as_int('x_deadzone_px', int(cfg['x_deadzone_px']), 0, 2000)
        cfg['y_deadzone_px'] = _as_int('y_deadzone_px', int(cfg['y_deadzone_px']), 0, 2000)
        cfg['smoothing_alpha'] = _as_float('smoothing_alpha', float(cfg['smoothing_alpha']), 0.0, 1.0)
        cfg['scan_when_lost'] = bool(source.get('scan_when_lost', cfg['scan_when_lost']))
        cfg['lost_timeout_s'] = _as_float('lost_timeout_s', float(cfg['lost_timeout_s']), 0.1, 60.0)
        cfg['target_distance_cm'] = _as_float('target_distance_cm', float(cfg['target_distance_cm']), 1.0, 500.0)
        cfg['distance_tolerance_cm'] = _as_float('distance_tolerance_cm', float(cfg['distance_tolerance_cm']), 0.0, 100.0)
        cfg['confidence_threshold'] = _as_float('confidence_threshold', float(cfg['confidence_threshold']), 0.0, 1.0)
        cfg['min_detection_area'] = _as_float('min_detection_area', float(cfg['min_detection_area']), 0.0, 1.0)
        cfg['min_target_area'] = _as_float('min_target_area', float(cfg['min_target_area']), 0.0, 1.0)
        cfg['edge_reject_margin_px'] = _as_int('edge_reject_margin_px', int(cfg['edge_reject_margin_px']), 0, 1000)
        cfg['lock_iou_threshold'] = _as_float('lock_iou_threshold', float(cfg['lock_iou_threshold']), 0.0, 1.0)
        cfg['switch_margin'] = _as_float('switch_margin', float(cfg['switch_margin']), 0.0, 10.0)
        cfg['min_lock_frames'] = _as_int('min_lock_frames', int(cfg['min_lock_frames']), 1, 100)
        cfg['process_every_n_frames'] = _as_int('process_every_n_frames', int(cfg['process_every_n_frames']), 1, 30)
        cfg['max_servo_step'] = _as_float('max_servo_step', float(cfg['max_servo_step']), 0.1, 90.0)
        cfg['servo_rate_limit_hz'] = _as_float('servo_rate_limit_hz', float(cfg['servo_rate_limit_hz']), 1.0, 120.0)
        return cfg, warnings

    def _update_detector_status(self) -> dict[str, Any]:
        status = {
            'opencv_available': self._cv_available,
            'active_detector': self._tracking_config.get('detector', 'haar_face'),
            'detectors': {},
            'yolo': {
                'available': False,
                'enabled_by_config': False,
                'dependency_ok': False,
                'model_ready': False,
                'reason': 'not_implemented_in_this_build',
            },
        }
        for name in ('haar_face', 'haar_body', 'motion'):
            detector = get_detector(name) if self._cv_available else None
            if detector is None:
                detector_status = {
                    'name': name,
                    'available': False,
                    'enabled_by_config': name == self._tracking_config.get('detector', 'haar_face'),
                    'dependency_ok': False,
                    'model_ready': False,
                    'reason': 'opencv_unavailable',
                }
            else:
                detector_status = detector.get_status()
                detector_status['enabled_by_config'] = name == self._tracking_config.get('detector', 'haar_face')
            status['detectors'][name] = detector_status
        self.runtime.state.tracking_detector_status = status
        active = status['detectors'].get(self._tracking_config.get('detector', 'haar_face'), {})
        self.runtime.state.tracking_detector_reason = active.get('reason')
        return status

    def get_detector_status(self) -> dict[str, Any]:
        return self._update_detector_status()

    def get_config(self) -> dict[str, Any]:
        return dict(self._tracking_config)

    def update_config(self, updates: dict[str, Any], persist: bool = True) -> tuple[dict[str, Any], list[str]]:
        merged = dict(self._tracking_config)
        merged.update(updates or {})
        normalized, warnings = self._normalize_tracking_config(merged)
        self._tracking_config = normalized
        self.tracker.apply_config(normalized)
        self.target_distance_cm = float(normalized.get('target_distance_cm', 30.0))
        self.distance_tolerance_cm = float(normalized.get('distance_tolerance_cm', 5.0))

        self.runtime.config['tracking'] = dict(normalized)
        self.runtime.state.tracking_mode = str(normalized.get('mode', 'camera_track'))
        self.runtime.state.tracking_detector = str(normalized.get('detector', 'haar_face'))
        self.runtime.state.tracking_detect_only_mode = bool(normalized.get('detect_only_mode', False))

        if 'detector' in (updates or {}) and self._cv_available:
            self.detector = get_detector(normalized.get('detector', 'haar_face'))

        if 'enabled' in (updates or {}):
            self.runtime.state.tracking_enabled = bool(normalized.get('enabled', False))

        self._update_detector_status()

        if persist:
            runtime_cfg = load_runtime_config()
            runtime_cfg['tracking'] = dict(normalized)
            save_runtime_config(runtime_cfg)

        return dict(normalized), warnings

    def start(self):
        if not self._cv_available:
            self.logger.warning('OpenCV or NumPy not installed; tracking support disabled.')
            self.runtime.state.tracking_disable_reason = 'opencv_unavailable'
            return
        if self.detector is None or not self.detector.is_available():
            self.logger.warning('Tracking detector unavailable; tracking support disabled.')
            self.runtime.state.tracking_disable_reason = 'detector_unavailable'
            self._update_detector_status()
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._tracking_loop, name='bob9k-tracking', daemon=True)
        self._thread.start()
        self.logger.info('Tracking background service started.')

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread = None

    def enable(self):
        if not self._cv_available:
            self.runtime.state.tracking_disable_reason = 'opencv_unavailable'
            self.logger.warning('Cannot enable tracking: OpenCV/NumPy unavailable.')
            return
        if self.detector is None or not self.detector.is_available():
            self.runtime.state.tracking_disable_reason = 'detector_unavailable'
            self.logger.warning('Cannot enable tracking: detector unavailable.')
            self._update_detector_status()
            return
        self.runtime.state.tracking_disable_reason = None
        self.runtime.state.tracking_enabled = True
        self.runtime.state.tracking_mode = str(self._tracking_config.get('mode', 'camera_track'))
        self.runtime.state.tracking_detect_only_mode = bool(self._tracking_config.get('detect_only_mode', False))
        self._tracking_config['enabled'] = True
        self.runtime.config['tracking'] = dict(self._tracking_config)
        self.logger.info('Object tracking ENABLED.')

    def disable(self, reason: str | None = None):
        if self.runtime.state.tracking_enabled:
            self.runtime.state.tracking_enabled = False
            self.logger.info('Object tracking DISABLED.')
            if not self.runtime.registry.motors.motion_locked:
                self.runtime.registry.motors.stop()
        self._tracking_config['enabled'] = False
        self.runtime.config['tracking'] = dict(self._tracking_config)
        self.runtime.state.tracking_target_acquired = False
        self.runtime.state.tracking_target_locked = False
        if reason is not None:
            self.runtime.state.tracking_disable_reason = reason

    def toggle(self):
        if self.runtime.state.tracking_enabled:
            self.disable()
        else:
            self.enable()

    def _filter_detections(self, detections, frame_w: int, frame_h: int):
        filtered = []
        margin = int(self._tracking_config.get('edge_reject_margin_px', 12))
        min_area_ratio = float(self._tracking_config.get('min_detection_area', 0.01))
        for det in detections or []:
            if det.confidence < float(self._tracking_config.get('confidence_threshold', 0.45)):
                continue
            area_ratio = float(det.area) / max(1.0, float(frame_w * frame_h))
            if area_ratio < min_area_ratio:
                continue
            if det.x <= margin or det.y <= margin or (det.x + det.w) >= (frame_w - margin) or (det.y + det.h) >= (frame_h - margin):
                continue
            if area_ratio > 0.85:
                continue
            filtered.append(det)
        return filtered

    def _tracking_loop(self):
        import cv2
        import numpy as np

        last_log_time = 0.0

        while not self._stop_event.is_set():
            time.sleep(0.05)

            if not self.runtime.state.tracking_enabled:
                continue

            if self.runtime.state.tracking_mode == 'off':
                self.disable(reason='mode_off')
                continue

            if getattr(self.runtime.registry.motors, 'motion_locked', False) or getattr(self.runtime.registry.motors, 'estop_latched', False):
                self.disable(reason='motion_blocked')
                continue

            if getattr(self.runtime.registry.motors, 'state', 'stopped') != 'stopped':
                self.runtime.registry.motors.stop()

            camera = getattr(self.runtime.registry, 'camera', None)
            camera_servo = getattr(self.runtime.registry, 'camera_servo', None)
            if not camera or not camera_servo:
                self.logger.warning('Tracking needs camera & camera_servo, but missing. Disabling.')
                self.disable(reason='hardware_missing')
                continue

            frame_bytes = camera.get_frame()
            if not frame_bytes:
                continue

            self._frame_counter += 1
            if (self._frame_counter % int(self._tracking_config.get('process_every_n_frames', 1))) != 0:
                continue

            try:
                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                raw_detections = self.detector.detect(frame) if self.detector else []
                detections = self._filter_detections(raw_detections, frame.shape[1], frame.shape[0])
                tracked, new_pan, new_tilt = self.tracker.update(
                    detections,
                    frame.shape[1],
                    frame.shape[0],
                    camera_servo.pan_angle,
                    camera_servo.tilt_angle,
                )

                self.runtime.state.tracking_error_x = tracked.error_x
                self.runtime.state.tracking_error_y = tracked.error_y
                self.runtime.state.tracking_target_locked = tracked.locked
                self.runtime.state.tracking_target_lock_frames = tracked.lock_frames
                self.runtime.state.tracking_target_switch_reason = tracked.switch_reason
                self.runtime.state.tracking_debug = {
                    'candidate_count': tracked.candidate_count,
                    'raw_candidate_count': len(raw_detections),
                    'filtered_candidate_count': len(detections),
                    'detect_only_mode': bool(self._tracking_config.get('detect_only_mode', False)),
                    'detector_status': self.runtime.state.tracking_detector_status,
                }

                if tracked.acquired and tracked.detection is not None:
                    self._last_target_seen_ts = time.time()
                    self.runtime.state.tracking_target_acquired = True
                    self.runtime.state.tracking_disable_reason = None
                    self.runtime.state.tracking_target_lost_age_s = 0.0
                    det = tracked.detection
                    self.runtime.state.tracking_box = (det.x, det.y, det.w, det.h)
                    self.runtime.state.tracking_target_label = det.label
                    self.runtime.state.tracking_target_confidence = round(float(det.confidence), 3)
                    self.runtime.state.tracking_target_area_ratio = round(float(det.area) / max(1.0, float(frame.shape[0] * frame.shape[1])), 4)
                    self.logger.debug(
                        'Tracking: target=%s area=%s err=(%.1f, %.1f) lock=%s',
                        det.label,
                        det.area,
                        tracked.error_x,
                        tracked.error_y,
                        tracked.locked,
                    )
                    servo_period = 1.0 / max(1.0, float(self._tracking_config.get('servo_rate_limit_hz', 15)))
                    if not bool(self._tracking_config.get('detect_only_mode', False)) and (time.time() - self._last_servo_write_ts) >= servo_period:
                        if new_pan is not None:
                            camera_servo.set_pan(int(round(new_pan)))
                        if new_tilt is not None:
                            camera_servo.set_tilt(int(round(new_tilt)))
                        self._last_servo_write_ts = time.time()
                    self.runtime.state.pan_angle = camera_servo.pan_angle
                    self.runtime.state.tilt_angle = camera_servo.tilt_angle
                else:
                    now = time.time()
                    timeout = float(self._tracking_config.get('lost_timeout_s', 2.0))

                    if self._last_target_seen_ts is not None and (now - self._last_target_seen_ts) <= timeout:
                        self.runtime.state.tracking_target_acquired = True
                        self.runtime.state.tracking_disable_reason = None
                        self.runtime.state.tracking_target_lost_age_s = round(now - self._last_target_seen_ts, 3)
                    else:
                        self.runtime.state.tracking_target_acquired = False
                        self.runtime.state.tracking_target_locked = False
                        self.runtime.state.tracking_box = None
                        self.runtime.state.tracking_target_label = None
                        self.runtime.state.tracking_target_confidence = None
                        self.runtime.state.tracking_target_area_ratio = None
                        self.runtime.state.tracking_target_lost_age_s = None if self._last_target_seen_ts is None else round(now - self._last_target_seen_ts, 3)
                        if self._last_target_seen_ts is not None:
                            self.runtime.state.tracking_disable_reason = 'target_lost'
                        if now - last_log_time > 2.0:
                            self.logger.info('Tracking: no targets detected in the last 2 seconds')
                            last_log_time = now

            except Exception as exc:
                self.logger.error(f'Error in tracking loop: {exc}')

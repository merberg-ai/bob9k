from __future__ import annotations

import threading
import time

from bob9k.config import load_runtime_config, save_runtime_config
from bob9k.vision.detectors import build_detector
from bob9k.vision.tracker import VisionTracker

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


class TrackingService:
    DEFAULTS = {
        'enabled': False,
        'mode': 'camera_track',
        'detector': 'face',
        'target_label': '',
        'yolo_model': 'yolov8n.pt',
        'enable_yolo': False,
        'yolo_imgsz': 320,
        'yolo_classes': [],
        'confidence_min': 0.45,
        'max_results': 20,
        'min_area': 1500,
        'min_target_area': 900,
        'pan_gain': 0.06,
        'tilt_gain': 0.06,
        'x_deadzone_px': 48,
        'y_deadzone_px': 36,
        'smoothing_alpha': 0.4,
        'scan_when_lost': True,
        'scan_step': 2,
        'scan_tilt_step': 0,
        'lost_timeout_s': 1.5,
        'process_every_n_frames': 3,
        'box_padding_px': 8,
        'show_labels': True,
        'show_crosshair': True,
        'show_metrics_overlay': True,
        'preferred_target': 'largest',
        'servo_idle_hold_s': 0.35,
        'invert_error_x': False,
        'invert_error_y': False,
        'jpeg_every_n_frames': 2,
        'idle_sleep_s': 0.02,
        'stats_log_interval_s': 10.0,
        'overlay_enabled': True,
        'show_confidence_bar': True,
        # --- object follow settings ---
        'follow_target_distance_cm': 60,
        'follow_distance_tolerance_cm': 15,
        'follow_drive_speed': 30,
        'follow_steer_gain': 0.6,
        'follow_use_ultrasonic': False,
        'follow_stop_distance_cm': 25,
        'follow_image_size_ratio_target': 0.25,
        'follow_image_size_tolerance': 0.06,
        'invert_pan_error': False,
    }

    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._stop = threading.Event()
        self._thread = None
        self._config = self._normalize(dict(runtime.config.get('tracking', {})))

        # Boot safety: never start in object_follow mode.
        # Prevents the robot from driving autonomously immediately on startup
        # (e.g. driving off a table or cliff after a reboot).
        # This reset is intentionally NOT persisted — runtime.yaml keeps the
        # user's saved mode preference so they can re-enable follow from the UI.
        if self._config.get('mode') == 'object_follow':
            self._config['mode'] = 'camera_track'
            runtime.config.setdefault('tracking', {})['mode'] = 'camera_track'
            logger.info(
                'Boot safety: tracking mode reset from object_follow → camera_track '
                '(not persisted; re-enable follow mode via the UI)'
            )

        self._detector = build_detector(self._config.get('detector', 'face'), self._config)
        self._tracker = VisionTracker(self._config)
        self._last_seen_ts = None
        self._last_move_ts = 0.0
        self._scan_dir = 1
        self._scan_tilt_dir = 1
        self._latest_jpeg = b''
        self._latest_detections = []
        self._latest_target = None
        self._fps_window_ts = time.time()
        self._fps_counter = 0
        self._fps_actual = 0.0
        self._process = psutil.Process() if psutil else None
        self._last_stats_log_ts = 0.0
        self._mjpeg_clients = 0
        self._mjpeg_clients_lock = threading.Lock()
        self._cv_ok = self._check_cv()
        self._sync_state_basics()

    def _check_cv(self) -> bool:
        try:
            import cv2  # noqa: F401
            import numpy as np  # noqa: F401
            return True
        except Exception:
            return False

    def _normalize(self, source: dict) -> dict:
        cfg = dict(self.DEFAULTS)
        cfg.update(source or {})
        cfg['enabled'] = bool(cfg.get('enabled', False))
        cfg['mode'] = str(cfg.get('mode', 'camera_track')).strip().lower()
        if cfg['mode'] not in {'off', 'camera_track', 'object_follow'}:
            cfg['mode'] = 'camera_track'
        detector = str(cfg.get('detector', 'face')).strip().lower()
        aliases = {'haar_face': 'face', 'haar_body': 'body'}
        cfg['detector'] = aliases.get(detector, detector)
        cfg['target_label'] = str(cfg.get('target_label', '')).strip().lower()
        raw_classes = cfg.get('yolo_classes', [])
        if isinstance(raw_classes, str):
            raw_classes = [x.strip().lower() for x in raw_classes.split(',') if x.strip()]
        cfg['yolo_classes'] = raw_classes
        cfg['preferred_target'] = str(cfg.get('preferred_target', 'largest')).strip().lower()
        for name in (
            'confidence_min', 'pan_gain', 'tilt_gain', 'smoothing_alpha', 'lost_timeout_s',
            'servo_idle_hold_s', 'idle_sleep_s', 'stats_log_interval_s',
            'follow_steer_gain', 'follow_image_size_ratio_target', 'follow_image_size_tolerance',
        ):
            cfg[name] = float(cfg.get(name, self.DEFAULTS[name]))
        for name in (
            'max_results', 'min_area', 'min_target_area', 'x_deadzone_px', 'y_deadzone_px', 'scan_step',
            'scan_tilt_step', 'process_every_n_frames', 'box_padding_px', 'yolo_imgsz', 'jpeg_every_n_frames',
            'follow_target_distance_cm', 'follow_distance_tolerance_cm', 'follow_drive_speed',
            'follow_stop_distance_cm',
        ):
            cfg[name] = int(cfg.get(name, self.DEFAULTS[name]))
        for name in (
            'scan_when_lost', 'show_labels', 'show_crosshair', 'show_metrics_overlay',
            'invert_error_x', 'invert_error_y', 'enable_yolo', 'overlay_enabled',
            'show_confidence_bar', 'follow_use_ultrasonic', 'invert_pan_error',
        ):
            cfg[name] = bool(cfg.get(name, self.DEFAULTS[name]))
        cfg['confidence_min'] = max(0.0, min(1.0, cfg['confidence_min']))
        cfg['smoothing_alpha'] = max(0.0, min(1.0, cfg['smoothing_alpha']))
        cfg['process_every_n_frames'] = max(1, cfg['process_every_n_frames'])
        cfg['box_padding_px'] = max(0, cfg['box_padding_px'])
        cfg['jpeg_every_n_frames'] = max(1, cfg['jpeg_every_n_frames'])
        cfg['yolo_imgsz'] = max(160, int(cfg['yolo_imgsz']))
        cfg['idle_sleep_s'] = max(0.005, float(cfg['idle_sleep_s']))
        cfg['stats_log_interval_s'] = max(3.0, float(cfg['stats_log_interval_s']))
        cfg['follow_drive_speed'] = max(0, min(100, cfg['follow_drive_speed']))
        cfg['follow_steer_gain'] = max(0.0, min(1.0, cfg['follow_steer_gain']))
        cfg['follow_target_distance_cm'] = max(5, cfg['follow_target_distance_cm'])
        cfg['follow_stop_distance_cm'] = max(5, cfg['follow_stop_distance_cm'])
        return cfg

    def _sync_state_basics(self):
        state = self.runtime.state
        state.tracking_enabled = bool(self._config.get('enabled', False))
        state.tracking_mode = self._config.get('mode', 'camera_track')
        state.tracking_detector = self._config.get('detector', 'face')
        state.tracking_preferred_target = self._config.get('preferred_target', 'largest')
        state.tracking_overlay_enabled = bool(self._config.get('overlay_enabled', True))
        state.tracking_detector_available = bool(self._detector.is_available()) if self._detector else False
        state.tracking_detector_status = self.get_detector_status()
        state.tracking_yolo_available = self.yolo_available()
        state.tracking_detector_details = self.get_detector_details()

    def get_config(self):
        return dict(self._config)

    def get_detector_status(self):
        det = self._detector
        if det is None:
            return 'missing'
        if hasattr(det, 'status'):
            try:
                return det.status()
            except Exception:
                return 'unknown'
        return 'ready' if det.is_available() else 'unavailable'

    def get_detector_details(self):
        det = self._detector
        name = self._config.get('detector', 'face')
        status = self.get_detector_status()
        available = bool(det.is_available()) if det else False
        details = {
            'selected': name,
            'available': available,
            'status': status,
            'yolo_available': self.yolo_available(),
            'enable_yolo': bool(self._config.get('enable_yolo', False)),
            'yolo_model': self._config.get('yolo_model', 'yolov8n.pt'),
            'yolo_classes': list(self._config.get('yolo_classes', []) or []),
            'detectors': {
                'face': {'available': True, 'status': 'ready'},
                'body': {'available': True, 'status': 'ready'},
                'motion': {'available': True, 'status': 'ready'},
                'yolo': {
                    'available': self.yolo_available() and bool(self._config.get('enable_yolo', False)),
                    'status': status if name == 'yolo' else ('available' if self.yolo_available() else 'unavailable: ultralytics import failed'),
                },
            },
        }
        if det is not None and hasattr(det, '_error') and getattr(det, '_error', None):
            details['reason'] = getattr(det, '_error')
        return details

    def yolo_available(self):
        try:
            from ultralytics import YOLO  # noqa: F401
            return True
        except Exception:
            return False

    def update_config(self, patch: dict, persist: bool = True):
        merged = dict(self._config)
        merged.update(patch or {})
        self._config = self._normalize(merged)
        self._tracker.apply_config(self._config)
        self.runtime.config['tracking'] = dict(self._config)
        self._detector = build_detector(self._config.get('detector', 'face'), self._config)
        self._sync_state_basics()
        if persist:
            runtime_cfg = load_runtime_config()
            runtime_cfg['tracking'] = dict(self._config)
            save_runtime_config(runtime_cfg)
        return dict(self._config), []

    def set_enabled(self, enabled: bool, persist: bool = False):
        self._config['enabled'] = bool(enabled)
        self.runtime.config['tracking'] = dict(self._config)
        self.runtime.state.tracking_enabled = bool(enabled)
        self.runtime.state.tracking_scan_active = False
        self.runtime.state.tracking_disable_reason = None if enabled else self.runtime.state.tracking_disable_reason
        if persist:
            runtime_cfg = load_runtime_config()
            runtime_cfg['tracking'] = dict(self._config)
            save_runtime_config(runtime_cfg)

    def enable(self):
        if not self._cv_ok:
            self.runtime.state.tracking_disable_reason = 'opencv_unavailable'
            return
        if self._detector is None or not self._detector.is_available():
            self.runtime.state.tracking_disable_reason = 'detector_unavailable'
            return
        self.set_enabled(True, persist=True)

    def disable(self, reason: str | None = None):
        self.set_enabled(False, persist=True)
        self.runtime.state.tracking_target_acquired = False
        self.runtime.state.tracking_box = None
        self.runtime.state.tracking_target_label = None
        self.runtime.state.tracking_target_confidence = None
        self.runtime.state.tracking_scan_active = False
        self.runtime.state.tracking_disable_reason = reason
        self.runtime.state.tracking_follow_state = 'stopped'
        motors = getattr(self.runtime.registry, 'motors', None)
        if motors and not getattr(motors, 'motion_locked', False):
            try:
                motors.stop()
            except Exception:
                pass
        steering = getattr(self.runtime.registry, 'steering', None)
        if steering:
            try:
                steering.center()
            except Exception:
                pass

    def toggle(self):
        if self.runtime.state.tracking_enabled:
            self.disable()
        else:
            self.enable()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name='bob9k-tracking')
        self._thread.start()
        self.logger.info('Tracking background service started. detector=%s', self._config.get('detector', 'face'))

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _distance_from_center(self, det, frame_w, frame_h):
        dx = det.center_x - (frame_w / 2.0)
        dy = det.center_y - (frame_h / 2.0)
        return (dx * dx) + (dy * dy)

    def _choose_target(self, detections, frame_w, frame_h):
        return self._tracker.choose_target(detections, frame_w, frame_h)

    def _draw_overlay(self, frame, detections, target):
        import cv2
        h, w = frame.shape[:2]
        pad = int(self._config.get('box_padding_px', 0))
        show_labels = self._config.get('show_labels', True)
        show_conf_bar = self._config.get('show_confidence_bar', True)

        for det in detections:
            is_target = (
                target and
                det.x == target.x and det.y == target.y and
                det.w == target.w and det.h == target.h
            )
            x1 = max(0, det.x - pad)
            y1 = max(0, det.y - pad)
            x2 = min(w - 1, det.x + det.w + pad)
            y2 = min(h - 1, det.y + det.h + pad)

            if is_target:
                color = (0, 255, 204)
                thickness = 2
                # Corner-cross style markers instead of plain rectangle
                cs = min(16, (x2 - x1) // 4, (y2 - y1) // 4)  # corner size
                cv2.line(frame, (x1, y1), (x1 + cs, y1), color, thickness)
                cv2.line(frame, (x1, y1), (x1, y1 + cs), color, thickness)
                cv2.line(frame, (x2, y1), (x2 - cs, y1), color, thickness)
                cv2.line(frame, (x2, y1), (x2, y1 + cs), color, thickness)
                cv2.line(frame, (x1, y2), (x1 + cs, y2), color, thickness)
                cv2.line(frame, (x1, y2), (x1, y2 - cs), color, thickness)
                cv2.line(frame, (x2, y2), (x2 - cs, y2), color, thickness)
                cv2.line(frame, (x2, y2), (x2, y2 - cs), color, thickness)
                # Thin full box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (*color[:2], 80), 1)
            else:
                color = (120, 120, 120)
                thickness = 1
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            if show_labels:
                label = f"{det.label} {det.confidence:.2f}" if det.confidence < 0.999 else det.label
                label_y = max(14, y1 - 6)
                cv2.putText(frame, label, (x1 + 2, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.46, color, 1, cv2.LINE_AA)

            if show_conf_bar and is_target:
                bar_w = x2 - x1
                filled = int(bar_w * max(0.0, min(1.0, float(det.confidence))))
                bar_y = y2 + 3
                if bar_y + 4 < h:
                    cv2.rectangle(frame, (x1, bar_y), (x2, bar_y + 4), (60, 60, 60), -1)
                    cv2.rectangle(frame, (x1, bar_y), (x1 + filled, bar_y + 4), (0, 255, 204), -1)

        if self._config.get('show_crosshair', True):
            cx, cy = w // 2, h // 2
            cv2.line(frame, (cx - 14, cy), (cx + 14, cy), (255, 255, 255), 1)
            cv2.line(frame, (cx, cy - 14), (cx, cy + 14), (255, 255, 255), 1)

        if self._config.get('show_metrics_overlay', True):
            state = self.runtime.state
            mode_tag = state.tracking_mode or 'camera_track'
            line1 = (
                f"det={state.tracking_detector} mode={mode_tag} "
                f"track={'on' if state.tracking_enabled else 'off'} "
                f"target={'yes' if state.tracking_target_acquired else 'no'}"
            )
            follow_str = ''
            if mode_tag == 'object_follow':
                dist = state.tracking_follow_distance_cm
                dist_s = f'{dist:.0f}cm' if dist is not None else '?cm'
                follow_str = f' follow={state.tracking_follow_state} ultra={dist_s}'
            line2 = (
                f"fps={self._fps_actual:.1f} pan={state.pan_angle} tilt={state.tilt_angle} "
                f"det={len(detections)} clients={self._mjpeg_clients}{follow_str}"
            )
            cv2.putText(frame, line1, (8, h - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, line2, (8, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    def _update_fps(self):
        self._fps_counter += 1
        now = time.time()
        elapsed = now - self._fps_window_ts
        if elapsed >= 1.0:
            self._fps_actual = self._fps_counter / elapsed
            self.runtime.state.tracking_fps_actual = round(self._fps_actual, 2)
            self._fps_counter = 0
            self._fps_window_ts = now

    def _move_to_target(self, frame, target):
        servo = getattr(self.runtime.registry, 'camera_servo', None)
        if servo is None or target is None:
            return
        next_pan, next_tilt = self._tracker.move_to_target(
            target,
            frame.shape[1],
            frame.shape[0],
            getattr(servo, 'pan_angle', self.runtime.state.pan_angle),
            getattr(servo, 'tilt_angle', self.runtime.state.tilt_angle),
        )
        if next_pan is not None:
            servo.set_pan(int(round(next_pan)))
        if next_tilt is not None:
            servo.set_tilt(int(round(next_tilt)))
        self.runtime.state.pan_angle = getattr(servo, 'pan_angle', self.runtime.state.pan_angle)
        self.runtime.state.tilt_angle = getattr(servo, 'tilt_angle', self.runtime.state.tilt_angle)
        self.runtime.state.tracking_scan_active = False
        self._last_move_ts = time.time()

    def _read_ultrasonic(self) -> float | None:
        """Return distance in cm from the ultrasonic sensor, or None."""
        sensor = getattr(self.runtime.registry, 'ultrasonic', None)
        if sensor is None:
            return None
        try:
            return sensor.read_cm()
        except Exception:
            return None

    def _follow_target(self, frame, target):
        """Drive motors and steer to follow the target object at a set distance.

        The camera servo still tracks the target via _move_to_target; this
        method additionally actuates drive motors and steering.
        """
        cfg = self._config
        motors = getattr(self.runtime.registry, 'motors', None)
        steering = getattr(self.runtime.registry, 'steering', None)
        if target is None:
            if motors:
                try:
                    motors.stop()
                except Exception:
                    pass
            if steering:
                try:
                    steering.center()
                except Exception:
                    pass
            self.runtime.state.tracking_follow_state = 'stopped'
            return

        frame_h, frame_w = frame.shape[:2]

        # --- Ultrasonic hard-stop check ---
        use_sonic = bool(cfg.get('follow_use_ultrasonic', False))
        sonic_dist = None
        if use_sonic:
            sonic_dist = self._read_ultrasonic()
            self.runtime.state.tracking_follow_distance_cm = sonic_dist

        stop_dist = float(cfg.get('follow_stop_distance_cm', 25))
        if use_sonic and sonic_dist is not None and sonic_dist <= stop_dist:
            if motors:
                try:
                    motors.stop()
                except Exception:
                    pass
            self.runtime.state.tracking_follow_state = 'stopped_obstacle'
            # Still allow servo to track, and steer
            self._move_to_target(frame, target)
            return

        # --- Drive direction based on distance estimate ---
        speed = max(0, min(100, int(cfg.get('follow_drive_speed', 30))))
        drive_state = 'stopped'
        if motors and not getattr(motors, 'motion_locked', False) and not getattr(motors, 'estop_latched', False):
            if use_sonic and sonic_dist is not None:
                # Use absolute distance from ultrasonic
                target_dist = float(cfg.get('follow_target_distance_cm', 60))
                tolerance = float(cfg.get('follow_distance_tolerance_cm', 15))
                if sonic_dist > target_dist + tolerance:
                    motors.forward(speed)
                    drive_state = 'forward'
                elif sonic_dist < target_dist - tolerance:
                    motors.backward(speed)
                    drive_state = 'backward'
                else:
                    motors.stop()
                    drive_state = 'stopped'
            else:
                # Fallback: use apparent image size ratio to estimate distance
                target_area_ratio = (target.w * target.h) / max(1, frame_w * frame_h)
                ratio_target = float(cfg.get('follow_image_size_ratio_target', 0.25))
                ratio_tol = float(cfg.get('follow_image_size_tolerance', 0.06))
                if target_area_ratio < ratio_target - ratio_tol:
                    motors.forward(speed)
                    drive_state = 'forward'
                elif target_area_ratio > ratio_target + ratio_tol:
                    motors.backward(speed)
                    drive_state = 'backward'
                else:
                    motors.stop()
                    drive_state = 'stopped'

        # --- Steering: True Heading Error (Pan Angle + Image Offset) ---
        if steering:
            servo = getattr(self.runtime.registry, 'camera_servo', None)
            steer_gain = float(cfg.get('follow_steer_gain', 0.6))
            center = getattr(steering, 'center_angle', 90)
            min_a = getattr(steering, 'min_angle', 45)
            max_a = getattr(steering, 'max_angle', 135)
            invert = bool(getattr(steering, 'invert', False))
            
            err_x = float(target.center_x - (frame_w / 2.0))
            
            if servo:
                current_pan = float(getattr(servo, 'pan_angle', 90))
                pan_center = float(getattr(servo, 'pan_center', 90))
                
                # 1. Error from the camera's physical pan angle
                pan_err_deg = current_pan - pan_center
                if cfg.get('invert_pan_error', False):
                    pan_err_deg = -pan_err_deg
                
                # 2. Residual error from the image frame
                # Assume a ~60 degree Horizontal Field of View for the PiCamera.
                # error in pixels * (60 degrees / frame width) = error in degrees.
                fov_degrees = 60.0
                img_err_deg = err_x * (fov_degrees / max(1.0, frame_w))
                
                # True heading error relative to the chassis
                total_err_deg = pan_err_deg + img_err_deg
                
                # Normalise to [-1.0, 1.0] assuming a max reasonable tracking angle of ~50 degrees
                norm_err = total_err_deg / 50.0
            else:
                # Fallback if servo is missing: just use image frame
                norm_err = err_x / max(1.0, frame_w / 2.0)

            # Apply a deadzone so small offsets don't cause constant jitter
            deadzone = float(cfg.get('x_deadzone_px', 48))
            norm_deadzone = deadzone / max(1.0, frame_w / 2.0)
            if abs(norm_err) < norm_deadzone:
                norm_err = 0.0
                
            # Clamp normalised error to [-1, 1]
            norm_err = max(-1.0, min(1.0, norm_err))
            
            # Flip direction when the steering hardware is inverted
            if invert:
                norm_err = -norm_err
                
            # Use the correct half-range for each steering direction
            if norm_err >= 0:
                steer_range = float(max_a - center)
            else:
                steer_range = float(center - min_a)
                
            target_angle = center + int(norm_err * steer_range * steer_gain)
            target_angle = max(min_a, min(max_a, target_angle))
            try:
                steering.set_angle(target_angle)
                self.runtime.state.steering_angle = steering.angle
            except Exception:
                pass

        self.runtime.state.tracking_follow_state = drive_state
        # Camera servo still tracks
        self._move_to_target(frame, target)

    def _scan_for_target(self):
        servo = getattr(self.runtime.registry, 'camera_servo', None)
        if servo is None:
            return
        if not bool(self._config.get('scan_when_lost', True)):
            self.runtime.state.tracking_scan_active = False
            return
        now = time.time()
        if self._last_seen_ts is not None and (now - self._last_seen_ts) < float(self._config.get('lost_timeout_s', 1.5)):
            self.runtime.state.tracking_scan_active = False
            return
        pan = int(getattr(servo, 'pan_angle', self.runtime.state.pan_angle))
        tilt = int(getattr(servo, 'tilt_angle', self.runtime.state.tilt_angle))
        step = int(self._config.get('scan_step', 2))
        tilt_step = int(self._config.get('scan_tilt_step', 0))
        pan += step * self._scan_dir
        if pan <= int(getattr(servo, 'pan_min', 40)) or pan >= int(getattr(servo, 'pan_max', 140)):
            self._scan_dir *= -1
        servo.set_pan(pan)
        if tilt_step:
            tilt += tilt_step * self._scan_tilt_dir
            if tilt <= int(getattr(servo, 'tilt_min', 40)) or tilt >= int(getattr(servo, 'tilt_max', 140)):
                self._scan_tilt_dir *= -1
            servo.set_tilt(tilt)
        self.runtime.state.pan_angle = getattr(servo, 'pan_angle', self.runtime.state.pan_angle)
        self.runtime.state.tilt_angle = getattr(servo, 'tilt_angle', self.runtime.state.tilt_angle)
        self.runtime.state.tracking_scan_active = True
        self._last_move_ts = time.time()

    def _current_rss_mb(self):
        if self._process is None:
            return None
        try:
            return round(self._process.memory_info().rss / (1024 * 1024), 1)
        except Exception:
            return None

    def _maybe_log_stats(self):
        now = time.time()
        interval = float(self._config.get('stats_log_interval_s', 10.0))
        if (now - self._last_stats_log_ts) < interval:
            return
        self._last_stats_log_ts = now
        self.logger.info(
            'Tracking stats: fps=%.2f rss_mb=%s detector=%s status=%s detections=%s clients=%s tracking=%s mode=%s',
            self._fps_actual,
            self._current_rss_mb(),
            self.runtime.state.tracking_detector,
            self.runtime.state.tracking_detector_status,
            self.runtime.state.tracking_last_detection_count,
            self._mjpeg_clients,
            self.runtime.state.tracking_enabled,
            self.runtime.state.tracking_mode,
        )

    def _should_encode_jpeg(self, frame_counter: int) -> bool:
        with self._mjpeg_clients_lock:
            client_count = self._mjpeg_clients
        self.runtime.state.tracking_mjpeg_clients = client_count
        if client_count <= 0 and not self._latest_jpeg:
            return True
        if client_count <= 0:
            return False
        every_n = max(1, int(self._config.get('jpeg_every_n_frames', 2)))
        return (frame_counter % every_n) == 0

    def _loop(self):
        frame_counter = 0
        camera = getattr(self.runtime.registry, 'camera', None)
        servo = getattr(self.runtime.registry, 'camera_servo', None)
        motors = getattr(self.runtime.registry, 'motors', None)
        while not self._stop.is_set():
            cfg = self._config
            if camera is None or servo is None:
                self.runtime.state.tracking_disable_reason = 'hardware_missing'
                time.sleep(0.2)
                camera = getattr(self.runtime.registry, 'camera', None)
                servo = getattr(self.runtime.registry, 'camera_servo', None)
                continue
            frame = camera.read_bgr() if hasattr(camera, 'read_bgr') else None
            if frame is None:
                time.sleep(0.05)
                continue
            frame_counter += 1
            every_n = max(1, int(cfg.get('process_every_n_frames', 3)))
            process_this = (frame_counter % every_n == 0)
            detections = self._latest_detections
            target = self._latest_target
            if process_this:
                try:
                    suppress_motion = (
                        cfg.get('detector') == 'motion' and
                        (time.time() - self._last_move_ts) < float(cfg.get('servo_idle_hold_s', 0.35))
                    )
                    detections = [] if suppress_motion else self._detector.detect(frame)
                    target = self._choose_target(detections, frame.shape[1], frame.shape[0])
                    self._latest_detections = detections
                    self._latest_target = target
                    self.runtime.state.tracking_last_detection_count = len(detections)
                    self.runtime.state.tracking_detector_available = bool(self._detector.is_available())
                    self.runtime.state.tracking_detector_status = self.get_detector_status()
                    self.runtime.state.tracking_detector_details = self.get_detector_details()
                    if target:
                        self._last_seen_ts = time.time()
                        self.runtime.state.tracking_target_acquired = True
                        self.runtime.state.tracking_box = (target.x, target.y, target.w, target.h)
                        self.runtime.state.tracking_target_label = target.label
                        self.runtime.state.tracking_target_confidence = float(target.confidence)
                        self.runtime.state.tracking_disable_reason = None
                    else:
                        self.runtime.state.tracking_target_acquired = False
                        self.runtime.state.tracking_box = None
                        self.runtime.state.tracking_target_label = None
                        self.runtime.state.tracking_target_confidence = None
                        if self._last_seen_ts is not None:
                            self.runtime.state.tracking_disable_reason = 'target_lost'
                except Exception as exc:
                    self.runtime.state.tracking_last_error = str(exc)
                    self.runtime.state.tracking_detector_status = f'error: {exc}'
                    self.runtime.state.tracking_target_acquired = False
                    self.runtime.state.tracking_box = None
                    self.runtime.state.tracking_target_label = None
                    self.runtime.state.tracking_target_confidence = None
                    self._latest_detections = []
                    self._latest_target = None
                    detections = []
                    target = None
                    self.logger.exception('Detector failure: %s', exc)

            if motors and (getattr(motors, 'motion_locked', False) or getattr(motors, 'estop_latched', False)):
                if self.runtime.state.tracking_enabled:
                    self.disable(reason='motion_blocked')

            mode = self.runtime.state.tracking_mode
            if self.runtime.state.tracking_enabled and mode != 'off':
                if mode == 'object_follow':
                    # Object follow: servo tracking + motor drive + steering
                    self._follow_target(frame, target)
                    if not target:
                        self._scan_for_target()
                else:
                    # camera_track mode: servo only; stop motors if moving
                    if motors and getattr(motors, 'state', 'stopped') != 'stopped':
                        try:
                            motors.stop()
                        except Exception:
                            pass
                    if target:
                        self._move_to_target(frame, target)
                    else:
                        self._scan_for_target()
            else:
                self.runtime.state.tracking_scan_active = False
                self.runtime.state.tracking_follow_state = 'stopped'

            self.runtime.state.tracking_frame_size = (int(frame.shape[1]), int(frame.shape[0]))
            self._update_fps()
            self.runtime.state.tracking_metrics = {
                'fps_target': getattr(camera, 'fps', None),
                'fps_actual': round(self._fps_actual, 2),
                'detections': self.runtime.state.tracking_last_detection_count,
                'camera_backend': getattr(camera, '_backend', 'picamera2'),
                'detector_status': self.runtime.state.tracking_detector_status,
                'scan_active': self.runtime.state.tracking_scan_active,
                'rss_mb': self._current_rss_mb(),
                'mjpeg_clients': self.runtime.state.tracking_mjpeg_clients,
                'jpeg_every_n_frames': int(cfg.get('jpeg_every_n_frames', 2)),
                'process_every_n_frames': int(cfg.get('process_every_n_frames', 3)),
                'yolo_imgsz': int(cfg.get('yolo_imgsz', 320)),
                'follow_state': self.runtime.state.tracking_follow_state,
                'follow_distance_cm': self.runtime.state.tracking_follow_distance_cm,
            }
            if bool(cfg.get('overlay_enabled', True)) and self._should_encode_jpeg(frame_counter):
                draw_frame = self._draw_overlay(frame.copy(), detections or [], target)
                self._latest_jpeg = camera.encode_jpeg(draw_frame) if hasattr(camera, 'encode_jpeg') else b''
            self._maybe_log_stats()
            time.sleep(max(float(cfg.get('idle_sleep_s', 0.02)), 1.0 / max(1, getattr(camera, 'fps', 20))))

    def mjpeg(self):
        with self._mjpeg_clients_lock:
            self._mjpeg_clients += 1
        self.runtime.state.tracking_mjpeg_clients = self._mjpeg_clients
        camera = getattr(self.runtime.registry, 'camera', None)
        fps = max(1, getattr(camera, 'fps', 20)) if camera else 20
        try:
            while not self._stop.is_set():
                frame = self._latest_jpeg
                if frame:
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
                else:
                    raw = camera.get_frame() if camera else b''
                    if raw:
                        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + raw + b'\r\n'
                time.sleep(max(0.02, 1.0 / fps))
        finally:
            with self._mjpeg_clients_lock:
                self._mjpeg_clients = max(0, self._mjpeg_clients - 1)
            self.runtime.state.tracking_mjpeg_clients = self._mjpeg_clients

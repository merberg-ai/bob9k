from __future__ import annotations

import threading
import time
import random

from bob9k.config import load_runtime_config, save_runtime_config
from bob9k.vision.detectors import build_detector

class PatrolService:
    DEFAULTS = {
        'enabled': False,
        'speed': 35,
        'avoidance_distance_cm': 30,
        'targets': '',  # comma separated
        'detection_behavior': 'log', # 'log' or 'follow'
        'scan_pan_min': 45,
        'scan_pan_max': 135,
        'scan_step': 2,
        'scan_tilt_angle': 90,
        'detector': 'yolo',
        'enable_yolo': True,
        'confidence_min': 0.45,
        'yolo_model': 'yolov8n.pt',
        'yolo_classes': [],
        'min_target_area': 1500,
        'process_every_n_frames': 5,
        'yolo_imgsz': 320,
        'max_results': 10,
    }

    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._stop = threading.Event()
        self._thread = None
        self._config = self._normalize(dict(runtime.config.get('patrol', {})))
        
        # Detector is shared or standalone? Better standalone for patrol, or use same builder
        self._detector = build_detector(self._config.get('detector', 'yolo'), self._config)
        
        self._scan_dir = 1
        self._avoiding = False
        self._avoid_step = 0
        self._avoid_ts = 0.0
        
        self._sync_state_basics()

    def _normalize(self, source: dict) -> dict:
        cfg = dict(self.DEFAULTS)
        cfg.update(source or {})
        cfg['enabled'] = bool(cfg.get('enabled', False))
        cfg['speed'] = max(0, min(100, int(cfg.get('speed', 35))))
        cfg['avoidance_distance_cm'] = max(10, int(cfg.get('avoidance_distance_cm', 30)))
        cfg['detection_behavior'] = str(cfg.get('detection_behavior', 'log')).strip().lower()
        cfg['scan_pan_min'] = int(cfg.get('scan_pan_min', 45))
        cfg['scan_pan_max'] = int(cfg.get('scan_pan_max', 135))
        cfg['scan_step'] = int(cfg.get('scan_step', 2))
        cfg['scan_tilt_angle'] = int(cfg.get('scan_tilt_angle', 90))
        cfg['confidence_min'] = max(0.0, min(1.0, float(cfg.get('confidence_min', 0.45))))
        
        # Parse targets
        raw_targets = cfg.get('targets', '')
        if isinstance(raw_targets, str):
            cfg['targets'] = [x.strip().lower() for x in raw_targets.split(',') if x.strip()]
        elif isinstance(raw_targets, list):
            cfg['targets'] = [str(x).strip().lower() for x in raw_targets]

        cfg['yolo_classes'] = list(cfg['targets']) # For YOLO detector optimization
        
        return cfg

    def _sync_state_basics(self):
        state = self.runtime.state
        state.patrol_enabled = bool(self._config.get('enabled', False))
        state.patrol_speed = self._config.get('speed', 35)
        state.patrol_mode = self._config.get('detection_behavior', 'log')
        state.patrol_targets = self._config.get('targets', [])
        
    def get_config(self):
        return dict(self._config)

    def update_config(self, patch: dict, persist: bool = True):
        merged = dict(self._config)
        merged.update(patch or {})
        if 'targets' in patch and isinstance(patch['targets'], str):
            merged['targets'] = patch['targets']
            
        self._config = self._normalize(merged)
        self.runtime.config['patrol'] = dict(self._config)
        
        if self._config.get('detector') != getattr(self._detector, 'name', None):
             self._detector = build_detector(self._config.get('detector', 'yolo'), self._config)
             
        self._sync_state_basics()
        if persist:
            runtime_cfg = load_runtime_config()
            runtime_cfg['patrol'] = dict(self._config)
            save_runtime_config(runtime_cfg)
        return dict(self._config), []

    def enable(self):
        try:
            self.runtime.state.patrol_last_error = None
            if self.runtime.tracking and self.runtime.state.tracking_enabled:
                self.runtime.tracking.disable(reason='patrol_override')
            
            self._config['enabled'] = True
            self.update_config(self._config, persist=True)
            self._avoiding = False
            self._avoid_step = 0
        except Exception as e:
            self.runtime.state.patrol_last_error = f"enable() error: {e}"
            self.logger.error(f"Patrol enable error: {e}")

    def disable(self, reason: str | None = None):
        try:
            self._config['enabled'] = False
            self.update_config(self._config, persist=True)
            self.runtime.state.patrol_drive_state = 'stopped'
            self.runtime.state.patrol_disable_reason = reason
            
            motors = getattr(self.runtime.registry, 'motors', None)
            if motors:
                try: motors.stop()
                except: pass
                
            steering = getattr(self.runtime.registry, 'steering', None)
            if steering:
                try: steering.center()
                except: pass
        except Exception as e:
            self.runtime.state.patrol_last_error = f"disable() error: {e}"
            self.logger.error(f"Patrol disable error: {e}")

    def toggle(self):
        if self.runtime.state.patrol_enabled:
            self.disable()
        else:
            self.enable()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name='bob9k-patrol')
        self._thread.start()
        self.logger.info('Patrol background service started.')

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self):
        camera = getattr(self.runtime.registry, 'camera', None)
        servo = getattr(self.runtime.registry, 'camera_servo', None)
        motors = getattr(self.runtime.registry, 'motors', None)
        ultrasonic = getattr(self.runtime.registry, 'ultrasonic', None)
        steering = getattr(self.runtime.registry, 'steering', None)
        
        frame_counter = 0

        while not self._stop.is_set():
            if not self._config.get('enabled', False):
                time.sleep(0.1)
                continue
                
            now = time.time()
            frame_counter += 1
            
            # --- 1. Driving & Avoidance ---
            if motors and ultrasonic and steering and not getattr(motors, 'motion_locked', False):
                dist = None
                try: dist = ultrasonic.read_cm()
                except: pass
                
                self.runtime.state.patrol_metrics['ultrasonic_cm'] = dist
                
                avoid_dist = float(self._config.get('avoidance_distance_cm', 30))
                speed = int(self._config.get('speed', 35))
                
                if self._avoiding:
                    if self._avoid_step == 1:
                        # Stop and wait
                        motors.stop()
                        if now - self._avoid_ts > 0.5:
                            self._avoid_step = 2
                            self._avoid_ts = now
                    elif self._avoid_step == 2:
                        # Reverse
                        motors.backward(speed)
                        if now - self._avoid_ts > 1.0:
                            self._avoid_step = 3
                            self._avoid_ts = now
                            # Random turn
                            steering.set_angle(random.choice([45, 135])) 
                    elif self._avoid_step == 3:
                        # Turn
                        motors.forward(speed)
                        if now - self._avoid_ts > 1.0:
                            # Resume forward
                            steering.center()
                            self._avoiding = False
                            self._avoid_step = 0
                            self.runtime.state.patrol_drive_state = 'forward'
                            motors.forward(speed)
                else:
                    if dist is not None and dist > 0 and dist < avoid_dist:
                        # Init avoidance
                        self._avoiding = True
                        self._avoid_step = 1
                        self._avoid_ts = now
                        self.runtime.state.patrol_drive_state = 'avoiding'
                        motors.stop()
                    else:
                        self.runtime.state.patrol_drive_state = 'forward'
                        steering.center()
                        motors.forward(speed)

            # --- 2. Scanning ---
            if servo:
                pan = int(getattr(servo, 'pan_angle', self.runtime.state.pan_angle))
                p_min = self._config.get('scan_pan_min', 45)
                p_max = self._config.get('scan_pan_max', 135)
                step = self._config.get('scan_step', 2)
                
                # Nudge tilt to fixed level during patrol
                servo.set_tilt(self._config.get('scan_tilt_angle', 90))
                
                pan += step * self._scan_dir
                if pan <= p_min or pan >= p_max:
                    self._scan_dir *= -1
                    pan = max(p_min, min(p_max, pan))
                
                servo.set_pan(pan)
                self.runtime.state.pan_angle = servo.pan_angle

            # --- 3. Detection ---
            if camera and self._detector and getattr(self._detector, 'is_available', lambda: False)():
                process_every = self._config.get('process_every_n_frames', 5)
                if frame_counter % process_every == 0:
                    try:
                        frame = camera.read()
                        if frame is not None:
                            detections = self._detector.detect(frame)
                            self.runtime.state.patrol_metrics['detections'] = len(detections)
                            
                            targets = self._config.get('targets', [])
                            matched = None
                            for det in detections:
                                if not targets or det.label.lower() in targets:
                                    if det.confidence >= float(self._config.get('confidence_min', 0.45)):
                                        matched = det
                                        break
                                        
                            if matched:
                                self.runtime.state.patrol_detect_count += 1
                                self.runtime.state.patrol_last_detected = matched.label
                                self.logger.info(f"Patrol detected target: {matched.label} ({matched.confidence:.2f})")
                                
                                behavior = self._config.get('detection_behavior', 'log')
                                if behavior == 'follow':
                                    self._switch_to_follow(matched.label)
                    except Exception as e:
                        self.runtime.state.patrol_last_error = f"detection loop error: {e}"
                        self.logger.error(f"Patrol detection error: {e}")

            time.sleep(0.05)

    def _switch_to_follow(self, label: str):
        self.logger.info(f"Patrol switching to follow mode for target: {label}")
        self.disable(reason='switched_to_follow')
        
        if self.runtime.tracking:
            self.runtime.tracking.update_config({
                'enabled': True,
                'mode': 'object_follow',
                'detector': self._config.get('detector', 'yolo'),
                'target_label': label,
            }, persist=True)

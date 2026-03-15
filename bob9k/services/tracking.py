from __future__ import annotations
import threading
import time

class TrackingService:
    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._thread = None
        self._stop_event = threading.Event()
        self.target_distance_cm = self.runtime.config.get('tracking', {}).get('target_distance_cm', 30.0)
        self.distance_tolerance_cm = self.runtime.config.get('tracking', {}).get('distance_tolerance_cm', 5.0)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._tracking_loop, name='bob9k-tracking', daemon=True)
        self._thread.start()
        self.logger.info("Tracking background service started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread = None

    def enable(self):
        if not self.runtime.state.tracking_enabled:
            self.runtime.state.tracking_enabled = True
            self.logger.info("Object tracking ENABLED.")

    def disable(self):
        if self.runtime.state.tracking_enabled:
            self.runtime.state.tracking_enabled = False
            self.logger.info("Object tracking DISABLED.")
            # Ensure motors stop when we disable tracking, if we control them
            from bob9k.services.safety import emergency_stop
            # Or just stop if not locked
            if not self.runtime.registry.motors.motion_locked:
                self.runtime.registry.motors.stop()

    def toggle(self):
        if self.runtime.state.tracking_enabled:
            self.disable()
        else:
            self.enable()

    def _tracking_loop(self):
        while not self._stop_event.is_set():
            time.sleep(0.1)
            
            if not self.runtime.state.tracking_enabled:
                continue

            # Check if motion is healthy
            if getattr(self.runtime.registry.motors, 'motion_locked', False) or getattr(self.runtime.registry.motors, 'estop_latched', False):
                self.disable()
                continue
            # Stop motors if they were moving
            if self.runtime.registry.motors.state != 'stopped':
                self.runtime.registry.motors.stop()

            # Phase 1: Ultrasonic distance tracking (mapped to camera pan/tilt instead of wheels)
            ultrasonic = self.runtime.registry.ultrasonic
            camera_servo = self.runtime.registry.camera_servo
            if not ultrasonic or not camera_servo:
                self.logger.warning("Tracking needs ultrasonic & camera servo, but missing. Disabling.")
                self.disable()
                continue
                
            distance_cm = ultrasonic.read_cm()
            if distance_cm is None:
                continue
                
            error = distance_cm - self.target_distance_cm
            
            if abs(error) <= self.distance_tolerance_cm:
                pass # Target is at perfect distance, keep camera still
            elif error > 0:
                # Object is farther than target, pan left (arbitrary mapping, usually we'd track visually)
                camera_servo.pan_left()
                self.runtime.state.pan_angle = camera_servo.pan_angle
            else:
                # Object is closer than target, pan right 
                camera_servo.pan_right()
                self.runtime.state.pan_angle = camera_servo.pan_angle

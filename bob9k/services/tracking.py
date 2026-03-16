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
        try:
            import cv2
            import numpy as np
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except ImportError:
            self.logger.error("OpenCV or Numpy not installed. Tracking disabled.")
            return

        while not self._stop_event.is_set():
            time.sleep(0.05)
            
            if not self.runtime.state.tracking_enabled:
                continue

            # Check if motion is healthy
            if getattr(self.runtime.registry.motors, 'motion_locked', False) or getattr(self.runtime.registry.motors, 'estop_latched', False):
                self.disable()
                continue
            # Stop motors if they were moving
            if getattr(self.runtime.registry.motors, 'state', 'stopped') != 'stopped':
                self.runtime.registry.motors.stop()

            camera = getattr(self.runtime.registry, 'camera', None)
            camera_servo = getattr(self.runtime.registry, 'camera_servo', None)
            
            if not camera or not camera_servo:
                self.logger.warning("Tracking needs camera & camera_servo, but missing. Disabling.")
                self.disable()
                continue
                
            frame_bytes = camera.get_frame()
            if not frame_bytes:
                continue
                
            try:
                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                    
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) > 0:
                    # Find the largest face
                    faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
                    x, y, w, h = faces[0]
                    
                    face_center_x = x + w / 2
                    face_center_y = y + h / 2
                    
                    frame_h, frame_w = frame.shape[:2]
                    frame_center_x = frame_w / 2
                    frame_center_y = frame_h / 2
                    
                    offset_x = face_center_x - frame_center_x
                    offset_y = face_center_y - frame_center_y
                    
                    deadzone_x = frame_w * 0.1
                    deadzone_y = frame_h * 0.1
                    
                    p_gain_pan = 0.05
                    p_gain_tilt = 0.05
                    
                    current_pan = camera_servo.pan_angle
                    current_tilt = camera_servo.tilt_angle
                    
                    target_pan = current_pan
                    target_tilt = current_tilt

                    # Calculate target pan
                    if abs(offset_x) > deadzone_x:
                        delta_pan = offset_x * p_gain_pan
                        if getattr(camera_servo, 'pan_invert', False):
                            delta_pan = -delta_pan
                        target_pan += delta_pan
                        
                    # Calculate target tilt
                    if abs(offset_y) > deadzone_y:
                        delta_tilt = offset_y * p_gain_tilt
                        if getattr(camera_servo, 'tilt_invert', False):
                            delta_tilt = -delta_tilt
                        target_tilt += delta_tilt
                        
                    # Apply low-pass filtering
                    alpha = 0.4
                    new_pan = (alpha * target_pan) + ((1 - alpha) * current_pan)
                    new_tilt = (alpha * target_tilt) + ((1 - alpha) * current_tilt)
                    
                    # Clamp angles
                    new_pan = max(0, min(180, new_pan))
                    new_tilt = max(0, min(180, new_tilt))
                    
                    # Set new angles
                    camera_servo.set_pan(new_pan)
                    camera_servo.set_tilt(new_tilt)
                    
                    self.runtime.state.pan_angle = camera_servo.pan_angle
                    
            except Exception as e:
                self.logger.error(f"Error in tracking loop: {e}")

from __future__ import annotations

import threading
import time
import math
import logging
from typing import Optional

try:
    import evdev
except ImportError:
    evdev = None


class GamepadService:
    """
    Background service that scans for and connects to an Xbox Wireless Controller
    (or generic gamepad) over Bluetooth on the Raspberry Pi 5.
    Maps left stick to motor drive controls, and right stick to camera pan tilt.
    """

    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._thread = None
        self._stop_event = threading.Event()
        self.device: Optional[evdev.InputDevice] = None
        
        # Deadzones to prevent drift when sticks return to center
        self.deadzone = 8000
        self.max_val = 32767.0
        
        self.mapping = self.runtime.config.get('gamepad_mapping', {
            'throttle_fwd': 'ABS_Z',     # Left Trigger
            'throttle_rev': 'ABS_RZ',    # Right Trigger
            'steering': 'ABS_X',         # Left Stick X
            'pan': 'ABS_RX',             # Right Stick X
            'tilt': 'ABS_RY',            # Right Stick Y
            'estop': 'BTN_B',
            'clear_estop': 'BTN_A',
            'lights_on': 'BTN_TR',       # Right Bumper
            'lights_off': 'BTN_TL',      # Left Bumper
            'camera_home': 'BTN_THUMBR', # Right Stick Click
            'steering_center': 'BTN_THUMBL' # Left Stick Click
        })

        # State tracking for axes
        self.axis_state = {
            'ABS_X': 0, 'ABS_Y': 0,
            'ABS_RX': 0, 'ABS_RY': 0,
            'ABS_Z': 0, 'ABS_RZ': 0,
            'ABS_HAT0X': 0, 'ABS_HAT0Y': 0,
        }
        
        # Timing state to prevent flooding the I2C bus with servo commands
        self.last_servo_update = 0
        self.servo_update_rate_s = 0.05  # 20 Hz max servo update rate

    def start(self):
        if evdev is None:
            self.logger.warning("evdev not installed; Xbox controller support disabled (Windows/Mac environment?).")
            return
            
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._connection_loop, name='bob9k-gamepad', daemon=True)
        self._thread.start()
        self.logger.info("Gamepad background service started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread = None
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

    def _find_gamepad(self) -> Optional[evdev.InputDevice]:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            name = dev.name.lower()
            if 'xbox' in name or 'gamepad' in name or 'controller' in name:
                self.logger.info("Gamepad connected: %s at %s", dev.name, dev.path)
                return dev
        return None

    def _connection_loop(self):
        while not self._stop_event.is_set():
            if self.device is None:
                try:
                    self.device = self._find_gamepad()
                except Exception as e:
                    self.logger.warning("Error searching for gamepad: %s", e)
                
                if self.device is None:
                    # Wait and try again if no gamepad paired/active
                    self._stop_event.wait(3.0)
                    continue
            
            try:
                self._read_events()
            except (OSError, evdev.EvdevError) as e:
                self.logger.warning("Gamepad disconnected or error reading: %s", e)
                try:
                    self.device.close()
                except Exception:
                    pass
                self.device = None
                self._stop_event.wait(1.0) # brief cooldown before searching again
            except Exception as e:
                self.logger.exception("Unexpected error in gamepad loop: %s", e)
                self.device = None
                self._stop_event.wait(3.0)

    def _apply_deadzone(self, value: int, maximum: float = None) -> float:
        if maximum is None:
            maximum = self.max_val
        if abs(value) < self.deadzone:
            return 0.0
        # Normalize to -1.0 .. 1.0 based on axis max
        return value / maximum
        
    def _read_events(self):
        """Blocking read for events until error or stopped"""
        for event in self.device.read_loop():
            if self._stop_event.is_set():
                break

            if event.type == evdev.ecodes.EV_KEY:
                # Handle face buttons
                key_event = evdev.categorize(event)
                if key_event.keystate == key_event.key_down:
                    self._handle_button(key_event.keycode)
                    
            elif event.type == evdev.ecodes.EV_ABS:
                # Handle analog sticks and triggers
                abs_code = evdev.ecodes.ABS[event.code]
                if abs_code in self.axis_state:
                    self.axis_state[abs_code] = event.value
                    self._process_axes()

    def _handle_button(self, keycode):
        if not self.runtime or not self.runtime.registry:
            return
            
        reg = self.runtime.registry
        m = self.mapping
        
        def is_mapped(action_name):
            mapped_key = m.get(action_name)
            if not mapped_key:
                return False
            if keycode == mapped_key:
                return True
            aliases = {
                'BTN_A': 'BTN_SOUTH', 'BTN_SOUTH': 'BTN_A',
                'BTN_B': 'BTN_EAST',  'BTN_EAST': 'BTN_B',
                'BTN_X': 'BTN_NORTH', 'BTN_NORTH': 'BTN_X',
                'BTN_Y': 'BTN_WEST',  'BTN_WEST': 'BTN_Y',
                'BTN_TR2': 'BTN_TR',  'BTN_TR': 'BTN_TR2',
                'BTN_TL2': 'BTN_TL',  'BTN_TL': 'BTN_TL2',
            }
            return keycode == aliases.get(mapped_key)

        if is_mapped('clear_estop'):
            if reg.motors.estop_latched:
                reg.motors.clear_estop()
                self.logger.info("Gamepad: E-STOP cleared by button")
                
        elif is_mapped('estop'):
            if not reg.motors.estop_latched:
                reg.motors.emergency_stop(latch=True)
                self.logger.warning("Gamepad: E-STOP triggered!")
                
        elif is_mapped('lights_on'): 
            if reg.lights:
               reg.lights.set_custom_color(255, 255, 255) # Headlights on
               
        elif is_mapped('lights_off'): 
            if reg.lights:
               reg.lights.off() # Headlights off
               
        elif is_mapped('camera_home'): 
             if reg.camera_servo:
                 reg.camera_servo.home()
                 
        elif is_mapped('steering_center'): 
             if reg.steering:
                 reg.steering.center()
                 
    def _process_axes(self):
        if not self.runtime or not self.runtime.registry:
            return
            
        reg = self.runtime.registry
        now = time.monotonic()
        m = self.mapping
        
        # 1. THROTTLE (Left/Right Triggers)
        # Triggers map 0 to 1023 or 0 to 255 depending on controller type.
        
        rev_val = self.axis_state.get(m.get('throttle_rev'), 0)
        fwd_val = self.axis_state.get(m.get('throttle_fwd'), 0)
        
        # Determine trigger max dynamically or fallback to 1023
        t_max = 1023.0
        
        forward_throttle = (fwd_val / t_max) if fwd_val > 10 else 0.0
        reverse_throttle = (rev_val / t_max) if rev_val > 10 else 0.0
        
        if forward_throttle > 0.05:
            speed = int(forward_throttle * 100)
            try:
                reg.motors.forward(speed)
            except RuntimeError as e:
                self.runtime.logger.debug("Gamepad forward blocked: %s", e)
        elif reverse_throttle > 0.05:
             # Reverse only happens if RT is not depressed
             speed = int(reverse_throttle * 100)
             try:
                 reg.motors.backward(speed)
             except RuntimeError as e:
                 self.runtime.logger.debug("Gamepad backward blocked: %s", e)
        else:
             reg.motors.stop()
             
        # 2. STEERING 
        if now - self.last_servo_update > self.servo_update_rate_s:
            ls_x_val = self._apply_deadzone(self.axis_state.get(m.get('steering'), 0))
            
            # Slew rate filtering (simple lerp) smoothing for steering
            if not hasattr(self, '_steer_target'):
                self._steer_target = reg.steering.angle
                
            steer_range = (reg.steering.max_angle - reg.steering.min_angle) / 2
            raw_target = 90 + (ls_x_val * steer_range)
            
            # Smoothing factor (alpha). Lower = smoother but more input lag.
            alpha = 0.35 
            self._steer_target = (alpha * raw_target) + ((1.0 - alpha) * self._steer_target)
            
            steer_out = int(self._steer_target)
            if abs(reg.steering.angle - steer_out) > 1:
                reg.steering.set_angle(steer_out)

            # 3. CAMERA PAN/TILT 
            rs_x_val = self._apply_deadzone(self.axis_state.get(m.get('pan'), 0))
            rs_y_val = self._apply_deadzone(self.axis_state.get(m.get('tilt'), 0))
            
            panned = False
            tilted = False
            
            # Camera smoothing
            if abs(rs_x_val) > 0:
               # Map to delta speed based on stick throw
               delta = int(rs_x_val * reg.camera_servo.pan_step * 0.5) 
               reg.camera_servo.set_pan(reg.camera_servo.pan_angle - delta) 
               panned = True
               
            if abs(rs_y_val) > 0:
                # Joystick Y is negative=up
                delta = int(rs_y_val * reg.camera_servo.tilt_step * 0.5)
                reg.camera_servo.set_tilt(reg.camera_servo.tilt_angle + delta)
                tilted = True
                
            if panned or tilted:
                self.last_servo_update = now

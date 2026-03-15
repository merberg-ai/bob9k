from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

try:
    import evdev
except ImportError:
    evdev = None


class GamepadService:
    """
    Background service for Xbox/generic controllers via evdev.

    Intended mapping:
      - Left stick X   -> steering
      - Left stick click -> steering center
      - Left trigger   -> brake/reverse
      - Right trigger  -> forward
      - Right stick X/Y -> camera pan/tilt
      - Right stick click -> camera home
    """

    DEFAULT_MAPPING = {
        'throttle_fwd': 'ABS_RZ',      # Right Trigger
        'throttle_rev': 'ABS_Z',       # Left Trigger
        'steering': 'ABS_X',           # Left Stick X
        'pan': 'ABS_RX',               # Right Stick X
        'tilt': 'ABS_RY',              # Right Stick Y
        'estop': 'BTN_B',
        'clear_estop': 'BTN_A',
        'lights_on': 'BTN_TR',         # Right Bumper
        'lights_off': 'BTN_TL',        # Left Bumper
        'camera_home': 'BTN_THUMBR',   # Right Stick Click
        'steering_center': 'BTN_THUMBL',  # Left Stick Click
    }

    BUTTON_ALIASES = {
        'BTN_A': 'BTN_SOUTH', 'BTN_SOUTH': 'BTN_A',
        'BTN_B': 'BTN_EAST',  'BTN_EAST': 'BTN_B',
        'BTN_X': 'BTN_NORTH', 'BTN_NORTH': 'BTN_X',
        'BTN_Y': 'BTN_WEST',  'BTN_WEST': 'BTN_Y',
        'BTN_TR2': 'BTN_TR',  'BTN_TR': 'BTN_TR2',
        'BTN_TL2': 'BTN_TL',  'BTN_TL': 'BTN_TL2',
    }

    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._thread = None
        self._stop_event = threading.Event()
        self.device: Optional[evdev.InputDevice] = None

        self.deadzone = 8000
        self.max_val = 32767.0
        self.mapping = self.runtime.config.get('gamepad_mapping', dict(self.DEFAULT_MAPPING))

        self.axis_state = {
            'ABS_X': 0, 'ABS_Y': 0,
            'ABS_RX': 0, 'ABS_RY': 0,
            'ABS_Z': 0, 'ABS_RZ': 0,
            'ABS_HAT0X': 0, 'ABS_HAT0Y': 0,
        }
        self.axis_ranges: dict[str, dict] = {}

        self.last_servo_update = 0.0
        self.servo_update_rate_s = 0.05  # 20 Hz max servo update rate
        self._last_drive_tuple = None
        self._last_button = None
        self._last_event_ts = None
        self._recent_events = deque(maxlen=60)

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
            name = (dev.name or '').lower()
            if 'xbox' in name or 'gamepad' in name or 'controller' in name:
                self.logger.info("Gamepad connected: %s at %s", dev.name, dev.path)
                self._read_abs_caps(dev)
                return dev
        return None

    def _read_abs_caps(self, dev) -> None:
        self.axis_ranges = {}
        try:
            caps = dev.capabilities(absinfo=True)
            for code, absinfo in caps.get(evdev.ecodes.EV_ABS, []):
                code_name = evdev.ecodes.bytype[evdev.ecodes.EV_ABS].get(code, str(code))
                if absinfo is None:
                    continue
                self.axis_ranges[code_name] = {
                    'min': int(absinfo.min),
                    'max': int(absinfo.max),
                    'flat': int(getattr(absinfo, 'flat', 0) or 0),
                    'fuzz': int(getattr(absinfo, 'fuzz', 0) or 0),
                    'resolution': int(getattr(absinfo, 'resolution', 0) or 0),
                    'value': int(getattr(absinfo, 'value', 0) or 0),
                }
                self.axis_state.setdefault(code_name, int(getattr(absinfo, 'value', 0) or 0))
            if self.axis_ranges:
                self.logger.info("Gamepad axis capabilities: %s", self.axis_ranges)
        except Exception as exc:
            self.logger.warning("Unable to read gamepad axis capabilities: %s", exc)

    def _connection_loop(self):
        while not self._stop_event.is_set():
            if self.device is None:
                try:
                    self.device = self._find_gamepad()
                except Exception as e:
                    self.logger.warning("Error searching for gamepad: %s", e)

                if self.device is None:
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
                self._stop_event.wait(1.0)
            except Exception as e:
                self.logger.exception("Unexpected error in gamepad loop: %s", e)
                self.device = None
                self._stop_event.wait(3.0)

    def _append_event(self, kind: str, name: str, value: int) -> None:
        now = time.time()
        self._last_event_ts = now
        self._recent_events.append({
            'ts': now,
            'kind': kind,
            'name': name,
            'value': int(value),
        })

    def _axis_meta(self, axis_name: str) -> dict:
        meta = self.axis_ranges.get(axis_name)
        if meta:
            return meta
        if axis_name in ('ABS_Z', 'ABS_RZ'):
            return {'min': 0, 'max': 1023, 'flat': 0, 'value': 0}
        return {'min': -32768, 'max': 32767, 'flat': self.deadzone, 'value': 0}

    def _normalized_axis(self, axis_name: str, value: int | None = None) -> float:
        if value is None:
            value = self.axis_state.get(axis_name, 0)
        meta = self._axis_meta(axis_name)
        amin = float(meta.get('min', -32768))
        amax = float(meta.get('max', 32767))
        flat = float(meta.get('flat', 0))
        value = float(value)

        if amax <= amin:
            return 0.0

        # Stick-like axis: signed around center.
        if amin < 0 < amax:
            center = (amin + amax) / 2.0
            span = max(1.0, (amax - amin) / 2.0)
            delta = value - center
            deadzone = max(flat, self.deadzone)
            if abs(delta) <= deadzone:
                return 0.0
            out = delta / span
            return max(-1.0, min(1.0, out))

        # Trigger-like axis: 0..1
        out = (value - amin) / (amax - amin)
        return max(0.0, min(1.0, out))

    def _mapped_key_matches(self, incoming: str, mapped: str | None) -> bool:
        if not mapped:
            return False
        return incoming == mapped or incoming == self.BUTTON_ALIASES.get(mapped)

    def _read_events(self):
        for event in self.device.read_loop():
            if self._stop_event.is_set():
                break

            if event.type == evdev.ecodes.EV_KEY:
                key_event = evdev.categorize(event)
                keycode = key_event.keycode
                if isinstance(keycode, list):
                    keycode = keycode[0] if keycode else None
                if not keycode:
                    continue
                self._append_event('key', str(keycode), int(key_event.keystate))
                self._last_button = str(keycode)
                if key_event.keystate == key_event.key_down:
                    self._handle_button(str(keycode))

            elif event.type == evdev.ecodes.EV_ABS:
                abs_code = evdev.ecodes.ABS.get(event.code, str(event.code))
                self.axis_state[abs_code] = int(event.value)
                self._append_event('abs', abs_code, int(event.value))
                self._process_axes()

    def _handle_button(self, keycode):
        if not self.runtime or not self.runtime.registry:
            return

        reg = self.runtime.registry
        m = self.mapping

        if self._mapped_key_matches(keycode, m.get('clear_estop')):
            if reg.motors.estop_latched:
                reg.motors.clear_estop()
                self.logger.info("Gamepad: E-STOP cleared by button")

        elif self._mapped_key_matches(keycode, m.get('estop')):
            if not reg.motors.estop_latched:
                reg.motors.emergency_stop(latch=True)
                self.logger.warning("Gamepad: E-STOP triggered!")

        elif self._mapped_key_matches(keycode, m.get('lights_on')):
            if reg.lights:
                reg.lights.set_custom_color(255, 255, 255)

        elif self._mapped_key_matches(keycode, m.get('lights_off')):
            if reg.lights:
                reg.lights.off()

        elif self._mapped_key_matches(keycode, m.get('camera_home')):
            if reg.camera_servo:
                reg.camera_servo.home()

        elif self._mapped_key_matches(keycode, m.get('steering_center')):
            if reg.steering:
                reg.steering.center()

    def _process_axes(self):
        if not self.runtime or not self.runtime.registry:
            return

        reg = self.runtime.registry
        now = time.monotonic()
        m = self.mapping

        # 1) DRIVE: triggers only
        fwd_axis = m.get('throttle_fwd')
        rev_axis = m.get('throttle_rev')
        forward_throttle = self._normalized_axis(fwd_axis) if fwd_axis else 0.0
        reverse_throttle = self._normalized_axis(rev_axis) if rev_axis else 0.0

        # Small noise guard for half-awake bluetooth controllers.
        if forward_throttle < 0.05:
            forward_throttle = 0.0
        if reverse_throttle < 0.05:
            reverse_throttle = 0.0

        drive_tuple = (round(forward_throttle, 3), round(reverse_throttle, 3))
        if drive_tuple != self._last_drive_tuple:
            self._last_drive_tuple = drive_tuple
            try:
                if forward_throttle > reverse_throttle and forward_throttle > 0.0:
                    reg.motors.forward(int(forward_throttle * 100))
                elif reverse_throttle > forward_throttle and reverse_throttle > 0.0:
                    reg.motors.backward(int(reverse_throttle * 100))
                else:
                    reg.motors.stop()
            except RuntimeError as e:
                self.runtime.logger.debug("Gamepad drive blocked: %s", e)

        # 2) STEERING + CAMERA, rate-limited to protect I2C bus
        if now - self.last_servo_update < self.servo_update_rate_s:
            return

        # Steering maps directly around configured center.
        steering_axis = m.get('steering')
        steer_val = self._normalized_axis(steering_axis) if steering_axis else 0.0
        if reg.steering and steering_axis:
            center = reg.steering.center_angle
            left_span = max(1, center - reg.steering.min_angle)
            right_span = max(1, reg.steering.max_angle - center)
            direction = -1.0 if reg.steering.invert else 1.0
            logical = steer_val * direction
            target = center + (logical * (right_span if logical >= 0 else left_span))
            steer_out = int(round(max(reg.steering.min_angle, min(reg.steering.max_angle, target))))
            if abs(reg.steering.angle - steer_out) >= 1:
                reg.steering.set_angle(steer_out)

        # Camera pan/tilt maps directly to configured ranges.
        if reg.camera_servo:
            pan_axis = m.get('pan')
            tilt_axis = m.get('tilt')
            pan_val = self._normalized_axis(pan_axis) if pan_axis else 0.0
            tilt_val = self._normalized_axis(tilt_axis) if tilt_axis else 0.0

            pan_dir = -1.0 if reg.camera_servo.pan_invert else 1.0
            tilt_dir = -1.0 if reg.camera_servo.tilt_invert else 1.0

            pan_center = reg.camera_servo.pan_center
            pan_left_span = max(1, pan_center - reg.camera_servo.pan_min)
            pan_right_span = max(1, reg.camera_servo.pan_max - pan_center)
            pan_logical = pan_val * pan_dir
            pan_target = pan_center + (pan_logical * (pan_right_span if pan_logical >= 0 else pan_left_span))
            pan_target = int(round(max(reg.camera_servo.pan_min, min(reg.camera_servo.pan_max, pan_target))))

            # Negative stick Y is usually up. Invert config decides final direction.
            tilt_center = reg.camera_servo.tilt_center
            tilt_up_span = max(1, tilt_center - reg.camera_servo.tilt_min)
            tilt_down_span = max(1, reg.camera_servo.tilt_max - tilt_center)
            tilt_logical = (-tilt_val) * tilt_dir
            tilt_target = tilt_center + (tilt_logical * (tilt_down_span if tilt_logical >= 0 else tilt_up_span))
            tilt_target = int(round(max(reg.camera_servo.tilt_min, min(reg.camera_servo.tilt_max, tilt_target))))

            if abs(reg.camera_servo.pan_angle - pan_target) >= 1:
                reg.camera_servo.set_pan(pan_target)
            if abs(reg.camera_servo.tilt_angle - tilt_target) >= 1:
                reg.camera_servo.set_tilt(tilt_target)

        self.last_servo_update = now

    def get_debug_snapshot(self) -> dict:
        axis_debug = {}
        for axis_name, raw in sorted(self.axis_state.items()):
            axis_debug[axis_name] = {
                'raw': raw,
                'normalized': round(self._normalized_axis(axis_name, raw), 4),
                'range': self.axis_ranges.get(axis_name),
            }
        return {
            'ok': True,
            'connected': self.device is not None,
            'device_name': getattr(self.device, 'name', None),
            'device_path': getattr(self.device, 'path', None),
            'mapping': dict(self.mapping),
            'axis_state': axis_debug,
            'last_button': self._last_button,
            'last_event_ts': self._last_event_ts,
            'recent_events': list(self._recent_events),
        }

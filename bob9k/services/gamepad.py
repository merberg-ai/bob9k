from __future__ import annotations

import threading
import time
<<<<<<< HEAD
=======
from collections import deque
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5
from typing import Optional


try:
    import evdev
except ImportError:
    evdev = None


class GamepadService:
    """
<<<<<<< HEAD
    Background service that scans for and connects to a Bluetooth/USB gamepad.

    Intended default mapping for bob9k:
      - Left stick X: steering left/right
      - Left stick click: center steering
      - Left trigger: brake / reverse
      - Right trigger: accelerate forward
      - Right stick: camera pan / tilt
      - Right stick click: camera home

    The previous implementation had three big problems:
      1) forward/reverse defaults were swapped,
      2) trigger values assumed a fixed 0..1023 range,
      3) stick motion ignored steering/camera invert + center config and used
         hardcoded 90-degree math.

    This version learns axis ranges from evdev, normalizes safely, and maps
    stick position directly to servo targets with light smoothing.
    """

    DEFAULT_MAPPING = {
        'throttle_fwd': 'ABS_RZ',       # Right Trigger
        'throttle_rev': 'ABS_Z',        # Left Trigger
        'steering': 'ABS_X',            # Left Stick X
        'pan': 'ABS_RX',                # Right Stick X
        'tilt': 'ABS_RY',               # Right Stick Y
        'pan_left': None,
        'pan_right': None,
        'tilt_up': None,
        'tilt_down': None,
        'estop_toggle': 'BTN_B',
        'lights_toggle': 'BTN_A',       # A button
        'camera_home': None,
        'steering_center': None
    }

    KEY_ALIASES = {
=======
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
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5
        'BTN_A': 'BTN_SOUTH', 'BTN_SOUTH': 'BTN_A',
        'BTN_B': 'BTN_EAST',  'BTN_EAST': 'BTN_B',
        'BTN_X': 'BTN_NORTH', 'BTN_NORTH': 'BTN_X',
        'BTN_Y': 'BTN_WEST',  'BTN_WEST': 'BTN_Y',
        'BTN_TR2': 'BTN_TR',  'BTN_TR': 'BTN_TR2',
        'BTN_TL2': 'BTN_TL',  'BTN_TL': 'BTN_TL2',
<<<<<<< HEAD
        'BTN_SELECT': 'BTN_BACK', 'BTN_BACK': 'BTN_SELECT',
        'BTN_START': 'BTN_MODE', 'BTN_MODE': 'BTN_START',
        'BTN_GUIDE': 'BTN_HOME', 'BTN_HOME': 'BTN_GUIDE',
=======
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5
    }

    def __init__(self, runtime, logger):
        self.runtime = runtime
        self.logger = logger
        self._thread = None
        self._btn_thread = None
        self._stop_event = threading.Event()
        self.device: Optional[evdev.InputDevice] = None
<<<<<<< HEAD
        self._btn_held = set()

        cfg = self.runtime.config
        self.mapping = cfg.get('gamepad_mapping', self.DEFAULT_MAPPING.copy())
        self.stick_deadzone = int(cfg.get('gamepad_stick_deadzone', 8000))
        self.trigger_deadzone = float(cfg.get('gamepad_trigger_deadzone', 0.06))
        self.servo_update_rate_s = float(cfg.get('gamepad_servo_update_rate_s', 0.05))
        self.steering_alpha = float(cfg.get('gamepad_steering_alpha', 0.35))
        self.camera_alpha = float(cfg.get('gamepad_camera_alpha', 0.15))
=======

        self.deadzone = 8000
        self.max_val = 32767.0
        self.mapping = self.runtime.config.get('gamepad_mapping', dict(self.DEFAULT_MAPPING))
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

        self.axis_state = {
            'ABS_X': 0, 'ABS_Y': 0,
            'ABS_RX': 0, 'ABS_RY': 0,
            'ABS_Z': 0, 'ABS_RZ': 0,
            'ABS_BRAKE': 0, 'ABS_GAS': 0,
            'ABS_HAT0X': 0, 'ABS_HAT0Y': 0,
        }
<<<<<<< HEAD
        self.axis_info: dict[str, tuple[int, int, int]] = {}
        self.available_axes: list[str] = []
        self.available_buttons: list[str] = []
        self.last_device_scan: list[dict[str, object]] = []
        self.last_input_event: dict[str, object] | None = None
        self.last_servo_update = 0.0
        self._steer_target = None
        self._pan_target = None
        self._tilt_target = None
        self._last_motor_cmd: tuple[str, int] | None = None
=======
        self.axis_ranges: dict[str, dict] = {}

        self.last_servo_update = 0.0
        self.servo_update_rate_s = 0.05  # 20 Hz max servo update rate
        self._last_drive_tuple = None
        self._last_button = None
        self._last_event_ts = None
        self._recent_events = deque(maxlen=60)
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

    def start(self):
        if evdev is None:
            self.logger.warning("evdev not installed; gamepad support disabled.")
            return
<<<<<<< HEAD
        if self._thread and self._thread.is_alive():
            return
=======

        if self._thread and self._thread.is_alive():
            return

>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._connection_loop, name='bob9k-gamepad', daemon=True)
        self._thread.start()
        self._btn_thread = threading.Thread(target=self._button_hold_loop, name='bob9k-gamepad-btns', daemon=True)
        self._btn_thread.start()
        self.logger.info("Gamepad background service started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread = None
        if self._btn_thread:
            self._btn_thread = None
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

    def _score_device(self, dev: evdev.InputDevice) -> tuple[int, dict[str, object]]:
        info: dict[str, object] = {
            'path': getattr(dev, 'path', ''),
            'name': getattr(dev, 'name', '') or 'Unknown input device',
            'score': 0,
            'axes': [],
            'buttons': [],
        }

        try:
            caps = dev.capabilities()
        except Exception as exc:
            info['error'] = str(exc)
            return 0, info

        name = str(info['name']).lower()
        if any(token in name for token in ('xbox', 'gamepad', 'controller', 'joystick')):
            info['score'] = int(info['score']) + 3

        abs_codes = []
        for entry in caps.get(evdev.ecodes.EV_ABS, []):
            code = entry[0] if isinstance(entry, tuple) else entry
            axis_name = evdev.ecodes.ABS.get(code)
            if isinstance(axis_name, list):
                axis_name = axis_name[0]
            if axis_name:
                abs_codes.append(axis_name)

        key_codes = []
        for entry in caps.get(evdev.ecodes.EV_KEY, []):
            code = entry[0] if isinstance(entry, tuple) else entry
            key_name = evdev.ecodes.KEY.get(code)
            if isinstance(key_name, list):
                key_name = key_name[0]
            if key_name:
                key_codes.append(key_name)

        info['axes'] = sorted(set(abs_codes))
        info['buttons'] = sorted(set(key_codes))

        preferred_axes = {
            'ABS_X': 2, 'ABS_Y': 2,
            'ABS_RX': 2, 'ABS_RY': 2,
            'ABS_Z': 2, 'ABS_RZ': 2,
            'ABS_GAS': 2, 'ABS_BRAKE': 2,
            'ABS_HAT0X': 1, 'ABS_HAT0Y': 1,
        }
        preferred_buttons = {
            'BTN_SOUTH': 1, 'BTN_A': 1, 'BTN_EAST': 1, 'BTN_B': 1,
            'BTN_THUMBL': 1, 'BTN_THUMBR': 1, 'BTN_TL': 1, 'BTN_TR': 1,
            'BTN_TL2': 1, 'BTN_TR2': 1, 'BTN_START': 1, 'BTN_SELECT': 1,
            'BTN_MODE': 1,
        }

        score = int(info['score'])
        for axis_name, points in preferred_axes.items():
            if axis_name in info['axes']:
                score += points
        for key_name, points in preferred_buttons.items():
            if key_name in info['buttons']:
                score += points

        if info['axes'] and info['buttons']:
            score += 2

        info['score'] = score
        return score, info

    def _find_gamepad(self) -> Optional[evdev.InputDevice]:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        candidates: list[tuple[int, evdev.InputDevice, dict[str, object]]] = []
        scanned: list[dict[str, object]] = []

        for dev in devices:
<<<<<<< HEAD
            try:
                score, info = self._score_device(dev)
            except Exception as exc:
                score, info = 0, {
                    'path': getattr(dev, 'path', ''),
                    'name': getattr(dev, 'name', '') or 'Unknown input device',
                    'score': 0,
                    'error': str(exc),
                }

            scanned.append(info)
            if score > 0:
                candidates.append((score, dev, info))

        self.last_device_scan = sorted(scanned, key=lambda item: (int(item.get('score', 0)), str(item.get('name', ''))), reverse=True)

        if not candidates:
            self.available_axes = []
            self.available_buttons = []
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        best_score, best_dev, best_info = candidates[0]
        self._load_axis_info(best_dev)
        self.available_axes = list(best_info.get('axes', []))
        self.available_buttons = list(best_info.get('buttons', []))
        self.logger.info(
            "Gamepad connected: %s at %s (score=%s axes=%s buttons=%s)",
            best_dev.name,
            best_dev.path,
            best_score,
            self.available_axes,
            self.available_buttons,
        )
        return best_dev

    def _load_axis_info(self, dev: evdev.InputDevice) -> None:
        self.axis_info = {}
        self.available_axes = []
        self.available_buttons = []
        try:
            caps = dev.capabilities(absinfo=True)
            for code, absinfo in caps.get(evdev.ecodes.EV_ABS, []):
                axis_name = evdev.ecodes.ABS.get(code)
                if isinstance(axis_name, list):
                    axis_name = axis_name[0]
                if not axis_name:
                    continue
                minimum = int(getattr(absinfo, 'min', 0))
                maximum = int(getattr(absinfo, 'max', 0))
                flat = int(getattr(absinfo, 'flat', 0))
                self.axis_info[axis_name] = (minimum, maximum, flat)
                self.available_axes.append(axis_name)

            for entry in caps.get(evdev.ecodes.EV_KEY, []):
                code = entry[0] if isinstance(entry, tuple) else entry
                key_name = evdev.ecodes.KEY.get(code)
                if isinstance(key_name, list):
                    key_name = key_name[0]
                if key_name:
                    self.available_buttons.append(key_name)

            self.available_axes = sorted(set(self.available_axes))
            self.available_buttons = sorted(set(self.available_buttons))

            if self.axis_info:
                self.logger.info("Gamepad axis ranges detected: %s", self.axis_info)
        except Exception as exc:
            self.logger.warning("Unable to read gamepad axis ranges: %s", exc)
            self.axis_info = {}
            self.available_axes = []
            self.available_buttons = []
=======
            name = (dev.name or '').lower()
            if 'xbox' in name or 'gamepad' in name or 'controller' in name:
                self.logger.info("Gamepad connected: %s at %s", dev.name, dev.path)
                self._read_abs_caps(dev)
                return dev
        return None
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

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
                    self._last_motor_cmd = None
                    self._steer_target = None
                    self._pan_target = None
                    self._tilt_target = None
                except Exception as e:
                    self.logger.warning("Error searching for gamepad: %s", e)

                if self.device is None:
                    self._stop_event.wait(3.0)
                    continue

            try:
                self._read_events()
            except (OSError, getattr(evdev, 'EvdevError', OSError)) as e:
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

<<<<<<< HEAD
    def _normalize_stick(self, axis_name: str, value: int) -> float:
        minimum, maximum, flat = self.axis_info.get(axis_name, (-32768, 32767, 0))
        center = (minimum + maximum) / 2.0
        magnitude = max(1.0, (maximum - minimum) / 2.0)
        deadzone = max(self.stick_deadzone, flat)
        offset = float(value) - center
        if abs(offset) <= deadzone:
            return 0.0
        out = offset / magnitude
        if out > 1.0:
            return 1.0
        if out < -1.0:
            return -1.0
        return out

    def _normalize_trigger(self, axis_name: str, value: int) -> float:
        minimum, maximum, flat = self.axis_info.get(axis_name, (0, 1023, 0))
        
        # Windows BT Xbox controllers often report triggers as full -32768 to 32767 axes
        # resting at ~32767 or exactly in the middle. We must detect and rely on the same stick logic.
        if minimum < 0:
            val = self._normalize_stick(axis_name, value)
            # Triggers only care about the "pressed" direction. If resting at 32767, pulling decreases it.
            # Convert the -1 to 1 range into a 0 to 1 magnitude throttle.
            return abs(val)

        if maximum <= minimum:
            return 0.0
        out = (float(value) - float(minimum)) / float(maximum - minimum)
        if out < 0.0:
            out = 0.0
        if out > 1.0:
            out = 1.0
        if out < self.trigger_deadzone:
            return 0.0
        return out
=======
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
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

    def _read_events(self):
        for event in self.device.read_loop():
            if self._stop_event.is_set():
                break

            if event.type == evdev.ecodes.EV_KEY:
<<<<<<< HEAD
                key_name = evdev.ecodes.KEY.get(event.code)
                if isinstance(key_name, list):
                    key_name = key_name[0]
                if not key_name:
                    key_name = f"BTN_{event.code}"
                
                # Expose the state so the frontend debug/mapping endpoints can read it
                self.axis_state[key_name] = event.value
                self.last_input_event = {'type': 'button', 'code': key_name, 'value': int(event.value), 'ts': time.time()}
                
                if event.value == 1:
                    self._handle_button(key_name, is_down=True)
                elif event.value == 0:
                    self._handle_button(key_name, is_down=False)
=======
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
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

            elif event.type == evdev.ecodes.EV_ABS:
                abs_code = evdev.ecodes.ABS[event.code]
                if isinstance(abs_code, list):
                    abs_code = abs_code[0]
                self.axis_state[abs_code] = event.value
                self.last_input_event = {'type': 'axis', 'code': abs_code, 'value': int(event.value), 'ts': time.time()}

    def _handle_button(self, keycode, is_down: bool):
        if not self.runtime or not self.runtime.registry:
            return

        reg = self.runtime.registry
        m = self.mapping
<<<<<<< HEAD

        def is_mapped(action_name):
            mapped_key = m.get(action_name)
            if not mapped_key:
                return False
            if keycode == mapped_key:
                return True
            alias1 = self.KEY_ALIASES.get(keycode)
            alias2 = self.KEY_ALIASES.get(mapped_key)
            if alias1 and alias1 == mapped_key:
                return True
            if alias2 and alias2 == keycode:
                return True
            return False

        holdable = ['pan_left', 'pan_right', 'tilt_up', 'tilt_down']
        for act in holdable:
            if is_mapped(act):
                if is_down:
                    self._btn_held.add(act)
                else:
                    self._btn_held.discard(act)

        if not is_down:
            return

        if is_mapped('estop_toggle'):
            if reg.motors.estop_latched:
                reg.motors.clear_estop()
                self.logger.info("Gamepad: E-STOP cleared by button toggle")
            else:
                reg.motors.emergency_stop(latch=True)
                self.logger.warning("Gamepad: E-STOP triggered by button toggle!")

        elif is_mapped('lights_toggle'):
            if hasattr(self.runtime, 'status_leds') and self.runtime.status_leds:
                self.runtime.status_leds.cycle_preset()
                self.logger.info("Gamepad: Lights cycled to next preset")

        elif is_mapped('camera_home'):
            if reg.camera_servo:
                reg.camera_servo.home()
                self._pan_target = reg.camera_servo.pan_angle
                self._tilt_target = reg.camera_servo.tilt_angle

        elif is_mapped('steering_center'):
            if reg.steering:
                reg.steering.center()
                self._steer_target = reg.steering.angle

    def _button_hold_loop(self):
        while not self._stop_event.is_set():
            if self._btn_held and getattr(self, 'runtime', None) and self.runtime.registry:
                reg = self.runtime.registry
                moved = False
                if reg.camera_servo:
                    if 'pan_left' in self._btn_held:
                        reg.camera_servo.pan_left()
                        self._pan_target = reg.camera_servo.pan_angle
                        moved = True
                    elif 'pan_right' in self._btn_held:
                        reg.camera_servo.pan_right()
                        self._pan_target = reg.camera_servo.pan_angle
                        moved = True
                    
                    if 'tilt_up' in self._btn_held:
                        reg.camera_servo.tilt_up()
                        self._tilt_target = reg.camera_servo.tilt_angle
                        moved = True
                    elif 'tilt_down' in self._btn_held:
                        reg.camera_servo.tilt_down()
                        self._tilt_target = reg.camera_servo.tilt_angle
                        moved = True
                        
                if moved:
                    self.last_servo_update = time.monotonic()
            
            # Continuously process all smoothed axis positions and motor states
            if self.device is not None:
                self._process_axes()

            time.sleep(self.servo_update_rate_s)

    def _set_motor_state(self, command: str, speed: int = 0) -> None:
        reg = self.runtime.registry
        command_key = (command, int(speed))
        if self._last_motor_cmd == command_key:
            return

        try:
            if command == 'forward':
                reg.motors.forward(speed)
            elif command == 'backward':
                reg.motors.backward(speed)
            else:
                reg.motors.stop()
            self._last_motor_cmd = command_key
        except RuntimeError as e:
            self.runtime.logger.debug("Gamepad motor command blocked: %s", e)
            self._last_motor_cmd = None
=======

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
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

    def _process_axes(self):
        if not self.runtime or not self.runtime.registry:
            return

        reg = self.runtime.registry
        now = time.monotonic()
        m = self.mapping
<<<<<<< HEAD

        # Triggers: RT forward, LT reverse.
        fwd_axis = m.get('throttle_fwd', 'ABS_RZ')
        rev_axis = m.get('throttle_rev', 'ABS_Z')
        forward_throttle = self._normalize_trigger(fwd_axis, self.axis_state.get(fwd_axis, 0))
        reverse_throttle = self._normalize_trigger(rev_axis, self.axis_state.get(rev_axis, 0))
        net = forward_throttle - reverse_throttle

        if net > self.trigger_deadzone:
            self._set_motor_state('forward', int(net * 100))
        elif net < -self.trigger_deadzone:
            self._set_motor_state('backward', int(abs(net) * 100))
        else:
            self._set_motor_state('stop', 0)

        # Steering: map stick position directly around configured center/range.
        steer_axis = m.get('steering', 'ABS_X')
        steer_norm = self._normalize_stick(steer_axis, self.axis_state.get(steer_axis, 0))
        if getattr(reg.steering, 'invert', False):
            steer_norm *= -1.0
        steer_center = reg.steering.center_angle
        steer_left_range = max(0, steer_center - reg.steering.min_angle)
        steer_right_range = max(0, reg.steering.max_angle - steer_center)
        raw_steer = steer_center + (steer_norm * (steer_right_range if steer_norm >= 0 else steer_left_range))

        if self._steer_target is None:
            self._steer_target = reg.steering.angle
        self._steer_target = (self.steering_alpha * raw_steer) + ((1.0 - self.steering_alpha) * self._steer_target)
        steer_out = int(round(self._steer_target))
        if abs(reg.steering.angle - steer_out) >= 1:
            reg.steering.set_angle(steer_out)

        # Camera: direct stick-to-angle mapping, honoring invert + center.
        pan_axis = m.get('pan', 'ABS_RX')
        tilt_axis = m.get('tilt', 'ABS_RY')
        pan_norm = self._normalize_stick(pan_axis, self.axis_state.get(pan_axis, 0))
        tilt_norm = self._normalize_stick(tilt_axis, self.axis_state.get(tilt_axis, 0))

        if getattr(reg.camera_servo, 'pan_invert', False):
            pan_norm *= -1.0
        if getattr(reg.camera_servo, 'tilt_invert', False):
            tilt_norm *= -1.0

        pan_center = reg.camera_servo.pan_center
        pan_left_range = max(0, pan_center - reg.camera_servo.pan_min)
        pan_right_range = max(0, reg.camera_servo.pan_max - pan_center)
        raw_pan = pan_center + (pan_norm * (pan_right_range if pan_norm >= 0 else pan_left_range))

        tilt_center = reg.camera_servo.tilt_center
        tilt_up_range = max(0, tilt_center - reg.camera_servo.tilt_min)
        tilt_down_range = max(0, reg.camera_servo.tilt_max - tilt_center)
        # Note: tilt_norm > 0 means stick up, which implies decreasing the angle (moving towards min)
        # tilt_norm < 0 means stick down, which implies increasing the angle (moving towards max)
        if tilt_norm > 0:
            raw_tilt = tilt_center - (tilt_norm * tilt_up_range)
        else:
            raw_tilt = tilt_center + (abs(tilt_norm) * tilt_down_range)

        if self._pan_target is None:
            self._pan_target = reg.camera_servo.pan_angle
        if self._tilt_target is None:
            self._tilt_target = reg.camera_servo.tilt_angle

        self._pan_target = (self.camera_alpha * raw_pan) + ((1.0 - self.camera_alpha) * self._pan_target)
        self._tilt_target = (self.camera_alpha * raw_tilt) + ((1.0 - self.camera_alpha) * self._tilt_target)

        pan_out = int(round(self._pan_target))
        tilt_out = int(round(self._tilt_target))
        moved = False
        if abs(reg.camera_servo.pan_angle - pan_out) >= 1:
            reg.camera_servo.set_pan(pan_out)
            moved = True
        if abs(reg.camera_servo.tilt_angle - tilt_out) >= 1:
            reg.camera_servo.set_tilt(tilt_out)
            moved = True

        if moved or abs(reg.steering.angle - steer_out) >= 0:
            self.last_servo_update = now
=======

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
>>>>>>> 8e1ddff7f283e2226df57327e7e42be2348b82f5

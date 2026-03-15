from __future__ import annotations

import threading
import time


class StatusLedService:
    def __init__(self, lights, state, config: dict, logger):
        self.lights = lights
        self.state = state
        self.config = config
        self.logger = logger
        self.colors = config['lights']['colors']
        self.current_state = 'OFF'
        self.custom_color = None
        self.battery_critical = False
        self._pattern = None
        self._stop_event = threading.Event()
        self._blink_thread = None

    def _start_pattern(self, pattern: str) -> None:
        if self._pattern == pattern and self._blink_thread and self._blink_thread.is_alive():
            return
        self._stop_pattern()
        self._pattern = pattern
        self._stop_event.clear()
        self._blink_thread = threading.Thread(target=self._blink_loop, name='bob9k-led-pattern', daemon=True)
        self._blink_thread.start()

    def _stop_pattern(self) -> None:
        self._stop_event.set()
        self._blink_thread = None
        self._pattern = None

    def _blink_loop(self) -> None:
        lights_cfg = self.config.get('lights', {})
        critical_interval = float(lights_cfg.get('critical_blink_interval_s', 0.5))
        police_interval = float(lights_cfg.get('police_interval_s', 0.25))
        red = self.colors.get('battery_critical', [255, 0, 0])
        blue = self.colors.get('police_blue', [0, 0, 255])
        off = self.colors.get('off', [0, 0, 0])
        left_red = True
        while not self._stop_event.is_set():
            pattern = self._pattern
            if pattern == 'BATTERY_CRITICAL':
                self.lights.set_both(*red)
                self.state.led_state = 'BATTERY_CRITICAL'
                if self._stop_event.wait(critical_interval):
                    break
                self.lights.set_both(*off)
                if self._stop_event.wait(critical_interval):
                    break
            elif pattern == 'POLICE':
                if left_red:
                    self.lights.set_left(*red); self.lights.set_right(*blue)
                else:
                    self.lights.set_left(*blue); self.lights.set_right(*red)
                left_red = not left_red
                self.state.led_state = 'POLICE'
                if self._stop_event.wait(police_interval):
                    break
            else:
                break

    def set_state(self, state_name: str) -> None:
        self.current_state = state_name.upper()
        if self.current_state != 'CUSTOM':
            self.custom_color = None
        self.apply()

    def set_custom_color(self, r: int, g: int, b: int) -> None:
        self.current_state = 'CUSTOM'
        self.custom_color = [int(r), int(g), int(b)]
        self.apply()

    def cycle_preset(self) -> None:
        cycle = ['OFF', 'ERROR', 'READY', 'BLUE', 'WHITE', 'CUSTOM']
        try:
            current_index = cycle.index(self.current_state)
        except ValueError:
            current_index = -1
            
        next_index = (current_index + 1) % len(cycle)
        next_state = cycle[next_index]
        
        # We need a fallback color for 'CUSTOM' if they haven't set one yet
        if next_state == 'CUSTOM' and self.custom_color is None:
            self.custom_color = [255, 0, 255] # Default to Purple so they know it works
            
        self.set_state(next_state)

    def clear_custom(self) -> None:
        self.custom_color = None
        self.set_state('READY')

    def set_battery_critical(self, active: bool) -> None:
        active = bool(active)
        if self.battery_critical == active:
            return
        self.battery_critical = active
        if active:
            self.logger.warning('Battery critical; flashing red eye LEDs')
            self.apply()
        else:
            self.logger.info('Battery no longer critical; restoring LED state')
            self.apply()

    def apply(self) -> None:
        if self.battery_critical:
            self.state.led_state = 'BATTERY_CRITICAL'
            self.state.led_custom = None
            self._start_pattern('BATTERY_CRITICAL')
            return

        if self.current_state == 'POLICE':
            self.state.led_state = 'POLICE'
            self.state.led_custom = None
            self._start_pattern('POLICE')
            return

        self._stop_pattern()

        if self.current_state == 'CUSTOM' and self.custom_color is not None:
            color = self.custom_color
        else:
            color = self.colors.get(self.current_state.lower(), self.colors.get('off', [0, 0, 0]))

        self.lights.set_both(*color)
        self.state.led_state = self.current_state
        self.state.led_custom = None if self.custom_color is None else {'r': color[0], 'g': color[1], 'b': color[2]}
        self.logger.info('LED state applied: %s -> %s', self.current_state, color)

    def close(self) -> None:
        self._stop_pattern()

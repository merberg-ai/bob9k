from __future__ import annotations
from dataclasses import dataclass
from bob9k.services.status_leds import StatusLedService
from bob9k.state import RuntimeState
@dataclass
class HardwareRegistry:
    hat: object | None = None
    lights: object | None = None
    motors: object | None = None
    steering: object | None = None
    camera_servo: object | None = None
    ultrasonic: object | None = None
    battery: object | None = None
    switches: object | None = None
    camera: object | None = None
@dataclass
class RuntimeContext:
    config: dict
    logger: object
    registry: HardwareRegistry
    state: RuntimeState
    telemetry: object
    status_leds: StatusLedService
    gamepad: object | None = None

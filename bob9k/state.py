from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RuntimeState:
    mode: str = 'idle'
    led_state: str = 'OFF'
    led_custom: dict[str, int] | None = None
    motor_state: str = 'stopped'
    speed: int = 0
    estop_latched: bool = False
    motion_locked: bool = False
    steering_angle: int = 90
    pan_angle: int = 90
    tilt_angle: int = 90
    telemetry: dict[str, Any] = field(default_factory=dict)
    tracking_enabled: bool = False
    tracking_mode: str = 'camera_track'
    tracking_detector: str = 'haar_face'
    tracking_target_acquired: bool = False
    tracking_disable_reason: str | None = None
    tracking_box: tuple[int, int, int, int] | None = None
    tracking_target_label: str | None = None
    tracking_target_confidence: float | None = None
    tracking_target_area_ratio: float | None = None
    tracking_error_x: float = 0.0
    tracking_error_y: float = 0.0
    tracking_target_locked: bool = False
    tracking_target_lock_frames: int = 0
    tracking_target_switch_reason: str | None = None
    tracking_target_lost_age_s: float | None = None
    tracking_detect_only_mode: bool = False
    tracking_detector_status: dict[str, Any] = field(default_factory=dict)
    tracking_detector_reason: str | None = None
    tracking_debug: dict[str, Any] = field(default_factory=dict)

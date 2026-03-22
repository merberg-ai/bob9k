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
    tracking_detector: str = 'face'
    tracking_target_acquired: bool = False
    tracking_disable_reason: str | None = None
    tracking_box: tuple[int, int, int, int] | None = None
    tracking_target_label: str | None = None
    tracking_target_confidence: float | None = None
    tracking_last_detection_count: int = 0
    tracking_frame_size: tuple[int, int] | None = None
    tracking_scan_active: bool = False
    tracking_metrics: dict[str, Any] = field(default_factory=dict)
    tracking_detector_available: bool = False
    tracking_detector_status: str = 'unknown'
    tracking_detector_details: dict[str, Any] = field(default_factory=dict)
    tracking_preferred_target: str = 'largest'
    tracking_yolo_available: bool = False
    tracking_overlay_enabled: bool = True
    tracking_fps_actual: float = 0.0
    tracking_mjpeg_clients: int = 0
    tracking_last_error: str | None = None
    tracking_follow_distance_cm: float | None = None
    tracking_follow_state: str = 'stopped'

    patrol_enabled: bool = False
    patrol_mode: str = 'log'
    patrol_drive_state: str = 'stopped'
    patrol_speed: int = 0
    patrol_targets: list[str] = field(default_factory=list)
    patrol_detect_count: int = 0
    patrol_last_detected: str | None = None
    patrol_metrics: dict[str, Any] = field(default_factory=dict)
    patrol_disable_reason: str | None = None

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Detection:
    label: str
    confidence: float
    x: int
    y: int
    w: int
    h: int
    center_x: float
    center_y: float
    area: int
    detector: str

    @property
    def area_ratio_hint(self) -> float:
        denom = max(1, self.w * self.h)
        return float(self.area) / float(denom)


@dataclass
class TrackedTarget:
    detection: Detection | None
    error_x: float = 0.0
    error_y: float = 0.0
    acquired: bool = False
    lost_age_s: float = 0.0
    locked: bool = False
    lock_frames: int = 0
    switch_reason: str | None = None
    candidate_count: int = 0

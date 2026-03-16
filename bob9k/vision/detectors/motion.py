from __future__ import annotations

import cv2

from bob9k.vision.detectors.base import BaseDetector
from bob9k.vision.models import Detection


class MotionDetector(BaseDetector):
    name = "motion"

    def __init__(self, min_area: int = 2000):
        self.min_area = min_area
        self._bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=200,
            varThreshold=40,
            detectShadows=False,
        )

    def is_available(self) -> bool:
        return self._bg_sub is not None

    def detect(self, frame) -> list[Detection]:
        if frame is None or not self.is_available():
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        mask = self._bg_sub.apply(gray)
        # morphological clean-up to reduce noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        # pick the largest contour that exceeds the minimum area
        best = max(contours, key=cv2.contourArea)
        if cv2.contourArea(best) < self.min_area:
            return []

        x, y, w, h = cv2.boundingRect(best)
        return [
            Detection(
                label='motion',
                confidence=1.0,
                x=int(x),
                y=int(y),
                w=int(w),
                h=int(h),
                center_x=float(x + w / 2.0),
                center_y=float(y + h / 2.0),
                area=int(w * h),
                detector=self.name,
            )
        ]

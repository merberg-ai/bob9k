from __future__ import annotations

import cv2

from bob9k.vision.detectors.base import BaseDetector
from bob9k.vision.models import Detection

class HaarBodyDetector(BaseDetector):
    name = "haar_body"

    def __init__(self):
        cascade_path = cv2.data.haarcascades + 'haarcascade_fullbody.xml'
        self.cascade = cv2.CascadeClassifier(cascade_path)

    def is_available(self) -> bool:
        return self.cascade is not None and not self.cascade.empty()

    def detect(self, frame):
        if frame is None or not self.is_available():
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bodies = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(30, 30),
        )

        detections = []
        for (x, y, w, h) in bodies:
            detections.append(
                Detection(
                    label='body',
                    confidence=1.0,
                    x=int(x),
                    y=int(y),
                    w=int(w),
                    h=int(h),
                    center_x=float(x + (w / 2.0)),
                    center_y=float(y + (h / 2.0)),
                    area=int(w * h),
                    detector=self.name,
                )
            )
        return detections

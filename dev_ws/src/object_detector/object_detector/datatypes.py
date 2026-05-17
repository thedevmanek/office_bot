from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass
class DetectionBox:
    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class ClusterSummary:
    x: float
    y: float
    range: float
    bearing: float
    angular_width: float
    points: int
    frame_id: str
    stamp: Any
    source: str
    observed_radius: float = 0.0

    def as_dict(self):
        return asdict(self)


@dataclass
class LocalizedDetection:
    point: Any
    cluster: ClusterSummary


@dataclass
class ObjectTrack:
    track_id: int
    class_name: str
    x: float
    y: float
    obstacle_radius: float
    confidence: float
    position_confidence: float
    confirmation_score: float
    detections: int
    confirmed: bool
    confirmed_at: Optional[float]
    last_seen: float
    snapshot: Optional[str] = None

    def as_dict(self):
        return asdict(self)


@dataclass
class NavigationStatus:
    state: str = "idle"
    message: str = "Waiting for detections."
    track_id: Optional[int] = None

    def as_dict(self):
        return asdict(self)

from dataclasses import dataclass
from datetime import datetime

Coordinate = tuple[float, float]


@dataclass(frozen=True)
class Place:
    id: str
    label: str
    coordinate: Coordinate
    time_zone: str


@dataclass(frozen=True)
class ProviderRoute:
    name: str
    highway: str
    geometry: tuple[Coordinate, ...]
    distance_meters: float
    duration_seconds: float
    segment_distances_meters: tuple[float, ...]
    segment_durations_seconds: tuple[float, ...]
    avoid: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteCheckpoint:
    number: int
    coordinate: Coordinate
    miles: float
    elapsed_seconds: float
    arrival: datetime
    time_zone: str

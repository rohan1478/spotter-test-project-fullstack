from geographiclib.geodesic import Geodesic
from bisect import bisect_left, bisect_right

from .route_models import Coordinate
from .validation import require_nonnegative

METERS_PER_MILE = 1609.344


def validate_coordinate(value) -> Coordinate:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError("Coordinates require [longitude, latitude].")
    lon, lat = value
    for number in (lon, lat):
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise ValueError("Coordinates must be finite numbers.")
        require_nonnegative(abs(number), "Coordinate magnitude")
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError("Coordinates are outside WGS84 bounds.")
    return float(lon), float(lat)


def segment_length(start: Coordinate, end: Coordinate) -> float:
    return Geodesic.WGS84.Inverse(start[1], start[0], end[1], end[0])["s12"]


def interpolate_coordinate(start: Coordinate, end: Coordinate, distance_meters: float) -> Coordinate:
    line = Geodesic.WGS84.InverseLine(start[1], start[0], end[1], end[0])
    position = line.Position(distance_meters)
    return position["lon2"], position["lat2"]


def geometry_fingerprint(geometry: tuple[Coordinate, ...]) -> tuple[Coordinate, ...]:
    points = []
    for coordinate in geometry:
        point = (round(coordinate[0], 5), round(coordinate[1], 5))
        if not points or point != points[-1]:
            points.append(point)
    return tuple(points)


def split_route_geometry(geometry, checkpoint_positions):
    cumulative = [0.0]
    for start, end in zip(geometry, geometry[1:]):
        cumulative.append(cumulative[-1] + segment_length(start, end))
    segments = []
    for (start_miles, start), (end_miles, end) in zip(checkpoint_positions, checkpoint_positions[1:]):
        first = bisect_right(cumulative, start_miles * METERS_PER_MILE + 1e-6)
        last = bisect_left(cumulative, end_miles * METERS_PER_MILE - 1e-6)
        segments.append((tuple(start), *geometry[first:last], tuple(end)))
    return tuple(segments)

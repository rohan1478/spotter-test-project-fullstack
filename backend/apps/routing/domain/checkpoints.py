from bisect import bisect_left
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from math import fsum

from .errors import RoutingError
from .geometry import METERS_PER_MILE, interpolate_coordinate, segment_length
from .route_models import Coordinate, ProviderRoute, RouteCheckpoint


def sample_checkpoints(
    route: ProviderRoute,
    departure: datetime,
    spacing_miles: int,
    timezone_lookup: Callable[[Coordinate], str],
    max_checkpoints: int = 1000,
) -> tuple[RouteCheckpoint, ...]:
    if spacing_miles not in (10, 25, 50) or isinstance(spacing_miles, bool):
        raise ValueError("Checkpoint spacing must be 10, 25, or 50 miles.")
    if departure.tzinfo is None or departure.utcoffset() is None:
        raise ValueError("Departure must include an explicit time zone.")
    if max_checkpoints < 2:
        raise ValueError("Allow at least two checkpoints.")
    lengths = tuple(segment_length(a, b) for a, b in zip(route.geometry, route.geometry[1:]))
    if len(lengths) != len(route.segment_durations_seconds):
        raise ValueError("Segment durations must align with route geometry.")
    distance = fsum(lengths)
    if distance <= 0:
        raise RoutingError("invalid_provider_response", "Routing provider returned empty road geometry.")
    spacing = spacing_miles * METERS_PER_MILE
    whole = int(distance // spacing)
    interior_count = max(0, whole - (1 if distance - whole * spacing <= 1e-6 else 0))
    targets = [0.0]
    if interior_count + 2 > max_checkpoints:
        raise RoutingError("too_many_checkpoints", "This trip exceeds the configured checkpoint limit.")
    targets.extend(index * spacing for index in range(1, interior_count + 1))
    targets.append(distance)
    cumulative_distance = [0.0]
    cumulative_time = [0.0]
    for length, duration in zip(lengths, route.segment_durations_seconds):
        cumulative_distance.append(cumulative_distance[-1] + length)
        cumulative_time.append(cumulative_time[-1] + duration)
    points = []
    departure = departure.astimezone(timezone.utc)
    for number, target in enumerate(targets):
        if number == 0:
            coordinate, elapsed = route.geometry[0], 0.0
        elif number == len(targets) - 1:
            coordinate, elapsed = route.geometry[-1], route.duration_seconds
        else:
            end_index = min(bisect_left(cumulative_distance, target), len(lengths))
            segment_index = max(0, end_index - 1)
            offset = target - cumulative_distance[segment_index]
            fraction = offset / lengths[segment_index]
            coordinate = interpolate_coordinate(
                route.geometry[segment_index], route.geometry[end_index], offset,
            )
            elapsed = cumulative_time[segment_index] + fraction * route.segment_durations_seconds[segment_index]
        points.append(RouteCheckpoint(
            number, coordinate, target / METERS_PER_MILE, elapsed,
            departure + timedelta(seconds=elapsed), timezone_lookup(coordinate),
        ))
    return tuple(points)

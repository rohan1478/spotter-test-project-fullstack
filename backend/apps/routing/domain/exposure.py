from collections.abc import Sequence
from math import fsum

from .choices import RISK_SCORES, RiskLevel
from .models import CheckpointWeather, RiskExposure, RiskInterval, RouteAssessment
from .risk import assess_weather
from .validation import require_positive


def assess_route(
    route_id: str,
    duration_minutes: float,
    checkpoints: Sequence[CheckpointWeather],
    load_weight_lb: float,
) -> RouteAssessment:
    if not isinstance(route_id, str) or not route_id.strip():
        raise ValueError("Route ID must be a nonempty string.")
    require_positive(duration_minutes, "Route duration")
    require_positive(load_weight_lb, "Load weight")
    points = tuple(checkpoints)
    if len(points) < 2 or any(not isinstance(point, CheckpointWeather) for point in points):
        raise ValueError("Supply at least two CheckpointWeather values, including both endpoints.")
    if points[0].miles != 0:
        raise ValueError("The first checkpoint must be at mile 0.")
    if any(end.miles <= start.miles for start, end in zip(points, points[1:])):
        raise ValueError("Checkpoint miles must be strictly increasing.")

    risks = tuple(assess_weather(point.weather, load_weight_lb) for point in points)
    intervals = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        endpoints = (risks[index].risk, risks[index + 1].risk)
        risk = None if None in endpoints else max(endpoints, key=RISK_SCORES.__getitem__)
        intervals.append(RiskInterval(start.miles, end.miles, risk))

    levels = (*RiskLevel, None)
    exposure = tuple(
        RiskExposure(level, fsum(item.distance_miles for item in intervals if item.risk == level))
        for level in levels
    )
    complete = all(item.complete for item in risks)
    distance = points[-1].miles
    overall_risk = max((item.risk for item in intervals), key=RISK_SCORES.__getitem__) if complete else None
    average = fsum(
        item.distance_miles / distance * RISK_SCORES[item.risk] for item in intervals
    ) if complete else None
    return RouteAssessment(
        route_id=route_id,
        duration_minutes=duration_minutes,
        distance_miles=distance,
        checkpoints=risks,
        intervals=tuple(intervals),
        exposure=exposure,
        risk=overall_risk,
        average_risk=average,
    )

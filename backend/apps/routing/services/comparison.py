from datetime import timedelta, timezone
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now as utc_now

from apps.routing.domain.errors import RoutingError
from apps.routing.domain.exposure import assess_route
from apps.routing.domain.forecast import ArrivalWeather, weather_at_arrival
from apps.routing.domain.geometry import split_route_geometry
from apps.routing.domain.models import CheckpointWeather, WeatherReading
from apps.routing.domain.recommendation import recommend_routes

from .routes import get_route_options
from .weather import get_forecasts


def analysis_cache_key(analysis_id):
    return f"analysis:v1:{analysis_id}"


def _ceil_hour(value):
    hour = value.replace(minute=0, second=0, microsecond=0)
    return hour if value == hour else hour + timedelta(hours=1)


def _route_explanation(assessment, recommendation, assessments):
    if not assessment.complete:
        return f"Not eligible: required weather is unavailable for {assessment.unknown_miles:g} miles."
    if not assessment.eligible:
        return f"Not eligible: this route contains {assessment.no_travel_miles:g} No Travel miles."
    if assessment.route_id == recommendation.recommended_route_id:
        return recommendation.explanation
    winner = next(route for route in assessments if route.route_id == recommendation.recommended_route_id)
    return recommend_routes([winner, assessment]).explanation


def compare_routes(trip, *, options_loader=None, weather_client=None, cache_backend=None, now=None):
    live_clock = now is None
    now = now or utc_now()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Comparison clock must be timezone-aware.")
    now = now.astimezone(timezone.utc)
    forecast_start = now.replace(minute=0, second=0, microsecond=0)
    horizon = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=settings.WEATHER_FORECAST_DAYS, hours=-1)
    if not forecast_start <= trip["departure"] <= horizon:
        raise RoutingError(
            "forecast_out_of_range", "Choose a departure within the available forecast window.",
            {"field": "departure", "startsAt": forecast_start.isoformat(), "endsAt": horizon.isoformat()},
        )
    options = (options_loader or get_route_options)(trip)
    backend = cache_backend if cache_backend is not None else cache
    points = [point for route in options["routes"] for point in route["checkpoints"]]
    covered = [point for point in points if forecast_start <= point["arrival"] <= horizon]
    if not covered:
        raise RoutingError("forecast_out_of_range", "No checkpoint arrivals fall within the forecast window.")
    start = min(point["arrival"] for point in covered).replace(minute=0, second=0, microsecond=0)
    end = max(_ceil_hour(point["arrival"]) for point in covered)
    if start == end:
        start -= timedelta(hours=1)
    collection = get_forecasts(
        [point["coordinate"] for point in covered], start, end, now,
        client=weather_client, cache_backend=backend,
    )
    assessments, routes = [], []
    warnings = list(options["warnings"])
    for route in options["routes"]:
        weather = []
        problems = set()
        for point in route["checkpoints"]:
            coordinate = tuple(point["coordinate"])
            if not forecast_start <= point["arrival"] <= horizon:
                selected = ArrivalWeather(WeatherReading(None, None, None), None, "forecast_out_of_range")
            elif coordinate in collection.failures:
                selected = ArrivalWeather(WeatherReading(None, None, None), None, collection.failures[coordinate].code)
            else:
                selected = weather_at_arrival(collection.forecasts[coordinate], point["arrival"])
            weather.append(selected)
            if selected.problem:
                problems.add(selected.problem)
        assessment = assess_route(
            route["id"], route["duration"],
            [CheckpointWeather(point["miles"], value.weather) for point, value in zip(route["checkpoints"], weather)],
            trip["loadWeight"],
        )
        assessments.append(assessment)
        geometries = split_route_geometry(
            route["geometry"], [(point["miles"], point["coordinate"]) for point in route["checkpoints"]],
        )
        checkpoints = []
        for point, value, risk in zip(route["checkpoints"], weather, assessment.checkpoints):
            checkpoints.append({
                **point, "wind": value.weather.wind_mph, "rain": value.weather.rain_in_per_hour,
                "snow": value.weather.snow_in_per_hour, "risk": risk.risk,
                "weatherStatus": "available" if risk.complete else "missing",
                "forecastTime": value.forecast_time, "riskReasons": list(risk.reasons),
            })
        routes.append({
            **route, "checkpoints": checkpoints, "risk": assessment.risk,
            "severeMiles": assessment.severe_miles, "highMiles": assessment.high_miles,
            "noTravelMiles": assessment.no_travel_miles, "unknownMiles": assessment.unknown_miles,
            "averageRisk": assessment.average_risk, "eligible": assessment.eligible,
            "complete": assessment.complete,
            "exposure": [{"risk": item.risk, "miles": item.miles} for item in assessment.exposure],
            "segments": [{
                "id": f"{route['id']}-segment-{index}", "geometry": geometry,
                "startMiles": interval.start_miles, "endMiles": interval.end_miles, "risk": interval.risk,
            } for index, (interval, geometry) in enumerate(zip(assessment.intervals, geometries))],
        })
        for problem in sorted(problems):
            warnings.append({"code": problem, "routeId": route["id"],
                             "message": "Some checkpoint weather is unavailable; this route cannot be recommended."})
    recommendation = recommend_routes(assessments)
    for route, assessment in zip(routes, assessments):
        route["recommended"] = route["id"] == recommendation.recommended_route_id
        route["explanation"] = _route_explanation(assessment, recommendation, assessments)
    if recommendation.recommended_route_id is None:
        warnings.append({"code": "no_recommendation", "message": recommendation.explanation})
    forecasts = list(collection.forecasts.values())
    retrieved = min(item.retrieved_at for item in forecasts)
    finished_at = utc_now() if live_clock else now
    expires = min(finished_at + timedelta(seconds=settings.ANALYSIS_CACHE_SECONDS),
                  retrieved + timedelta(seconds=settings.WEATHER_CACHE_SECONDS))
    lifetime = (expires - finished_at).total_seconds()
    if lifetime <= 0:
        raise RoutingError("forecast_expired", "Forecast data expired during comparison. Please retry.")
    analysis_id = str(uuid4())
    canonical_trip = {**trip, "originPlace": options["resolvedPlaces"]["origin"],
                      "destinationPlace": options["resolvedPlaces"]["destination"]}
    result = {
        "analysisId": analysis_id, "expiresAt": expires, "routes": routes, "trip": canonical_trip,
        "resolvedPlaces": options["resolvedPlaces"], "forecastStart": forecast_start,
        "forecastMetadata": {
            "provider": "Open-Meteo", "retrievedAt": retrieved,
            "startsAt": min(item.times[0] for item in forecasts),
            "endsAt": max(item.times[-1] for item in forecasts), "stepHours": 1,
            "units": {"wind": "mph", "rain": "in/hr", "snow": "in/hr"},
            "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
            "windSampling": "linear-interpolation", "precipitationSampling": "preceding-hour-containing-eta",
        },
        "recommendedRouteId": recommendation.recommended_route_id,
        "recommendationReason": recommendation.explanation,
        "rankedRouteIds": list(recommendation.ranked_route_ids), "warnings": warnings,
    }
    backend.set(analysis_cache_key(analysis_id), {"result": result, "options": options, "trip": canonical_trip},
                timeout=max(1, int(lifetime)))
    return result

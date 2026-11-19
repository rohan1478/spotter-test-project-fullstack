from datetime import timedelta, timezone
from hashlib import sha256
from math import ceil
from uuid import UUID, uuid4

from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now as utc_now

from apps.routing.domain.choices import RISK_SCORES, RiskLevel
from apps.routing.domain.corridor import build_corridor_grid
from apps.routing.domain.errors import RoutingError
from apps.routing.domain.forecast import weather_at_arrival
from apps.routing.domain.risk import assess_weather

from .comparison import analysis_cache_key
from .weather import get_forecasts

HOURS = 48


def corridor_cache_key(analysis_id):
    configuration = (
        settings.CORRIDOR_BUFFER_MILES, settings.CORRIDOR_GRID_MILES,
        settings.CORRIDOR_MAX_CELLS, settings.CORRIDOR_MAX_CANDIDATES,
        settings.CORRIDOR_MAX_VERTICES, settings.CORRIDOR_MAX_RADIUS_KM,
        settings.WEATHER_MAX_LOCATIONS, settings.WEATHER_FORECAST_DAYS,
        settings.WEATHER_CACHE_SECONDS,
    )
    digest = sha256(repr(configuration).encode()).hexdigest()[:16]
    return f"corridor:v1:{analysis_id}:{digest}"


def _load_analysis(analysis_id, backend, now):
    try:
        identifier = str(UUID(str(analysis_id)))
    except (ValueError, AttributeError):
        raise RoutingError("analysis_expired", "Analysis unavailable or expired. Compare the trip again.") from None
    record = backend.get(analysis_cache_key(identifier))
    if not record or record["result"]["expiresAt"] <= now:
        raise RoutingError("analysis_expired", "Analysis unavailable or expired. Compare the trip again.")
    return identifier, record


def get_corridor_forecast(analysis_id, *, weather_client=None, cache_backend=None, now=None):
    live_clock = now is None
    now = now or utc_now()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Corridor clock must be timezone-aware.")
    now = now.astimezone(timezone.utc)
    backend = cache_backend if cache_backend is not None else cache
    identifier, record = _load_analysis(analysis_id, backend, now)
    key = corridor_cache_key(identifier)
    cached = backend.get(key)
    if cached and cached["expiresAt"] > now:
        return cached
    lock_key, owner = key + ":lock", str(uuid4())
    batches = ceil(settings.CORRIDOR_MAX_CELLS / settings.WEATHER_BATCH_SIZE)
    lock_seconds = max(30, ceil(settings.PROVIDER_TIMEOUT_SECONDS * (batches + 1) + 30))
    if not backend.add(lock_key, owner, timeout=lock_seconds):
        raise RoutingError("corridor_in_progress", "This corridor forecast is being prepared. Retry shortly.")
    try:
        return _build_corridor(identifier, record, key, backend, weather_client, now, live_clock)
    finally:
        if backend.get(lock_key) == owner:
            backend.delete(lock_key)


def _build_corridor(identifier, record, key, backend, weather_client, now, live_clock):
    grid = build_corridor_grid(
        [route["geometry"] for route in record["options"]["routes"]],
        buffer_miles=settings.CORRIDOR_BUFFER_MILES, spacing_miles=settings.CORRIDOR_GRID_MILES,
        max_cells=min(settings.CORRIDOR_MAX_CELLS, settings.WEATHER_MAX_LOCATIONS),
        max_candidates=settings.CORRIDOR_MAX_CANDIDATES, max_vertices=settings.CORRIDOR_MAX_VERTICES,
        max_radius_km=settings.CORRIDOR_MAX_RADIUS_KM,
    )
    start = record["result"]["forecastStart"]
    end = start + timedelta(hours=HOURS)
    horizon = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=settings.WEATHER_FORECAST_DAYS, hours=-1)
    request_end = min(end, horizon)
    request_start = start if request_end > start else start - timedelta(hours=1)
    collection = get_forecasts([cell.coordinate for cell in grid.cells], request_start, request_end, now,
                               client=weather_client, cache_backend=backend)
    frames, problems = [], set()
    load = record["trip"]["loadWeight"]
    for offset in range(HOURS + 1):
        stamp = start + timedelta(hours=offset)
        scores = []
        for cell in grid.cells:
            if stamp > horizon:
                scores.append(None)
                problems.add("forecast_out_of_range")
                continue
            if cell.coordinate in collection.failures:
                scores.append(None)
                problems.add(collection.failures[cell.coordinate].code)
                continue
            selected = weather_at_arrival(collection.forecasts[cell.coordinate], stamp)
            risk = assess_weather(selected.weather, load)
            scores.append(None if risk.risk is None else RISK_SCORES[risk.risk])
            if selected.problem:
                problems.add(selected.problem)
        missing = scores.count(None)
        frames.append({"offsetHours": offset, "time": stamp, "riskScores": scores,
                       "complete": missing == 0, "missingCellCount": missing})
    finished_at = utc_now() if live_clock else now
    _load_analysis(identifier, backend, finished_at)
    retrieved = min(item.retrieved_at for item in collection.forecasts.values())
    expires = min(record["result"]["expiresAt"], retrieved + timedelta(seconds=settings.WEATHER_CACHE_SECONDS))
    if expires <= finished_at:
        raise RoutingError("forecast_expired", "Corridor data expired during preparation. Compare the trip again.")
    warnings = [{"code": problem, "message": "Some corridor cells or forecast hours are unavailable and remain unknown."}
                for problem in sorted(problems)]
    if grid.coarsened:
        warnings.append({"code": "corridor_grid_coarsened", "message": "Grid spacing was increased to fit the configured location budget."})
    result = {
        "analysisId": identifier, "forecastStart": start, "expiresAt": expires,
        "complete": all(frame["complete"] for frame in frames),
        "grid": {
            "bufferMiles": grid.buffer_miles, "requestedSpacingMiles": grid.requested_spacing_miles,
            "spacingMiles": grid.spacing_miles, "coarsened": grid.coarsened,
            "cellCount": len(grid.cells), "center": grid.center,
            "projection": "local-azimuthal-equidistant", "boundary": grid.boundary,
            "cells": [{"id": cell.id, "coordinate": cell.coordinate, "geometry": cell.geometry} for cell in grid.cells],
        },
        "frames": frames,
        "riskLevels": [{"score": RISK_SCORES[risk], "risk": risk.value,
                        "label": "No Travel" if risk == RiskLevel.NO_TRAVEL else risk.value.title()}
                       for risk in RiskLevel],
        "forecastMetadata": {
            "provider": "Open-Meteo", "retrievedAt": retrieved,
            "startsAt": min(item.times[0] for item in collection.forecasts.values()),
            "endsAt": max(item.times[-1] for item in collection.forecasts.values()),
            "stepHours": 1, "units": {"wind": "mph", "rain": "in/hr", "snow": "in/hr"},
            "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
            "windSampling": "instant-at-frame-hour", "precipitationSampling": "preceding-hour-containing-eta",
        },
        "warnings": warnings,
    }
    if not collection.failures:
        backend.set(key, result, timeout=max(1, int((expires - finished_at).total_seconds())))
    return result

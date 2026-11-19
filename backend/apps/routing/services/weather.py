from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache

from apps.routing.domain.errors import RoutingError
from apps.routing.domain.forecast import HourlyForecast
from apps.routing.domain.geometry import validate_coordinate
from apps.routing.domain.route_models import Coordinate
from apps.routing.providers.open_meteo import OpenMeteoClient


@dataclass
class ForecastCollection:
    forecasts: dict[Coordinate, HourlyForecast]
    failures: dict[Coordinate, RoutingError]


def forecast_key(coordinate, start, end):
    value = f"{coordinate!r}|{start.isoformat()}|{end.isoformat()}|mph-mm-cm"
    return "forecast:v1:" + sha256(value.encode()).hexdigest()


def get_forecasts(coordinates, start: datetime, end: datetime, now: datetime, *, client=None, cache_backend=None):
    client = client or OpenMeteoClient(settings.PROVIDER_TIMEOUT_SECONDS)
    backend = cache_backend if cache_backend is not None else cache
    coordinates = tuple(dict.fromkeys(validate_coordinate(point) for point in coordinates))
    if len(coordinates) > settings.WEATHER_MAX_LOCATIONS:
        raise RoutingError("too_many_weather_locations", "This trip exceeds the configured weather location limit.")
    keys = {point: forecast_key(point, start, end) for point in coordinates}
    cached = backend.get_many(keys.values())
    forecasts, missing, failures = {}, [], {}
    for point in coordinates:
        item = cached.get(keys[point])
        if (isinstance(item, HourlyForecast)
                and timedelta(0) <= now - item.retrieved_at < timedelta(seconds=settings.WEATHER_CACHE_SECONDS)):
            forecasts[point] = item
        else:
            missing.append(point)
    size = settings.WEATHER_BATCH_SIZE
    batches = [missing[index:index + size] for index in range(0, len(missing), size)]
    if batches:
        with ThreadPoolExecutor(max_workers=settings.WEATHER_MAX_WORKERS) as pool:
            pending = {pool.submit(client.fetch, batch, start, end, retrieved_at=now): batch for batch in batches}
            for future in as_completed(pending):
                batch = pending[future]
                try:
                    results = future.result()
                except RoutingError as error:
                    failures.update((point, error) for point in batch)
                    continue
                updates = {}
                for point, item in zip(batch, results):
                    forecasts[point] = item
                    updates[keys[point]] = item
                backend.set_many(updates, timeout=settings.WEATHER_CACHE_SECONDS)
    if not forecasts and failures:
        raise next(failures[point] for point in coordinates if point in failures)
    return ForecastCollection(forecasts, failures)

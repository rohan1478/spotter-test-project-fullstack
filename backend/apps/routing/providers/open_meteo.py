from datetime import datetime, timezone
from decimal import Decimal

from apps.routing.domain.forecast import HourlyForecast
from apps.routing.domain.geometry import validate_coordinate
from apps.routing.domain.models import WeatherReading
from apps.routing.domain.validation import require_nonnegative

from .http import ProviderHTTPClient

VARIABLES = ("wind_speed_10m", "rain", "showers", "snowfall")
EXPECTED_UNITS = {"time": "unixtime", "wind_speed_10m": "mp/h", "rain": "mm", "showers": "mm", "snowfall": "cm"}


class OpenMeteoClient(ProviderHTTPClient):
    def __init__(self, timeout_seconds=15, transport=None):
        super().__init__("Open-Meteo", "", timeout_seconds, transport, requires_api_key=False)

    def fetch(self, coordinates, start: datetime, end: datetime, *, retrieved_at: datetime):
        coordinates = tuple(validate_coordinate(point) for point in coordinates)
        body = self.get_json("https://api.open-meteo.com/v1/forecast", {
            "latitude": ",".join(str(point[1]) for point in coordinates),
            "longitude": ",".join(str(point[0]) for point in coordinates),
            "hourly": ",".join(VARIABLES), "wind_speed_unit": "mph",
            "precipitation_unit": "mm", "timeformat": "unixtime", "timezone": "GMT",
            "start_hour": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
            "end_hour": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        }, allow_list=True)
        items = body if isinstance(body, list) else [body]
        if len(items) != len(coordinates):
            raise self.error("invalid_provider_response", "Open-Meteo returned a different location count.")
        try:
            return tuple(self._parse(item, coordinate, retrieved_at, index)
                         for index, (item, coordinate) in enumerate(zip(items, coordinates)))
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            raise self.error("invalid_provider_response", "Open-Meteo returned malformed hourly forecasts or unexpected units.") from None

    def _parse(self, body, coordinate, retrieved_at, index):
        if "location_id" in body and (isinstance(body["location_id"], bool) or body["location_id"] != index):
            raise ValueError("Forecast location order is inconsistent.")
        if body.get("utc_offset_seconds") != 0:
            raise ValueError("Expected UTC timestamps.")
        if any(body["hourly_units"].get(key) != unit for key, unit in EXPECTED_UNITS.items()):
            raise ValueError("Unexpected hourly units.")
        hourly = body["hourly"]
        raw_times = hourly["time"]
        if not isinstance(raw_times, list) or len(raw_times) < 2:
            raise ValueError("Expected at least two hourly samples.")
        for stamp in raw_times:
            require_nonnegative(stamp, "Forecast timestamp")
        times = tuple(datetime.fromtimestamp(stamp, timezone.utc) for stamp in raw_times)
        if any(stamp.minute or stamp.second or stamp.microsecond for stamp in times):
            raise ValueError("Forecast times must be hourly UTC boundaries.")
        if any((b - a).total_seconds() != 3600 for a, b in zip(times, times[1:])):
            raise ValueError("Hourly samples must be ordered and contiguous.")
        for variable in VARIABLES:
            values = hourly[variable]
            if not isinstance(values, list) or len(values) != len(times):
                raise ValueError("Hourly arrays must align with timestamps.")
            for value in values:
                if value is not None:
                    require_nonnegative(value, variable)
        readings = []
        for wind, rain, showers, snow in zip(*(hourly[variable] for variable in VARIABLES)):
            liquid = None if rain is None or showers is None else float(
                (Decimal(str(rain)) + Decimal(str(showers))) / Decimal("25.4")
            )
            snowfall = None if snow is None else float(Decimal(str(snow)) / Decimal("2.54"))
            readings.append(WeatherReading(wind, liquid, snowfall))
        return HourlyForecast(coordinate, times, tuple(readings), retrieved_at)

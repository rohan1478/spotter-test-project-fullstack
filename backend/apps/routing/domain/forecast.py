from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import WeatherReading
from .route_models import Coordinate


@dataclass(frozen=True)
class HourlyForecast:
    coordinate: Coordinate
    times: tuple[datetime, ...]
    readings: tuple[WeatherReading, ...]
    retrieved_at: datetime


@dataclass(frozen=True)
class ArrivalWeather:
    weather: WeatherReading
    forecast_time: datetime | None
    problem: str | None = None


def weather_at_arrival(forecast: HourlyForecast, arrival: datetime) -> ArrivalWeather:
    if arrival.tzinfo is None or arrival.utcoffset() is None:
        raise ValueError("Arrival must be timezone-aware.")
    arrival = arrival.astimezone(timezone.utc)
    end = bisect_left(forecast.times, arrival)
    if end == len(forecast.times) or arrival < forecast.times[0]:
        return ArrivalWeather(WeatherReading(None, None, None), None, "forecast_out_of_range")
    reading = forecast.readings[end]
    wind = reading.wind_mph
    if forecast.times[end] != arrival:
        previous = forecast.readings[end - 1].wind_mph
        if previous is None or wind is None:
            wind = None
        else:
            fraction = (arrival - forecast.times[end - 1]).total_seconds() / 3600
            wind = previous + (wind - previous) * fraction
    weather = WeatherReading(wind, reading.rain_in_per_hour, reading.snow_in_per_hour)
    missing = any(value is None for value in (wind, weather.rain_in_per_hour, weather.snow_in_per_hour))
    return ArrivalWeather(weather, forecast.times[end], "missing_weather" if missing else None)

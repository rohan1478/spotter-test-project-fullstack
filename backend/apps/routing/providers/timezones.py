from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.routing.domain.errors import RoutingError
from apps.routing.domain.geometry import validate_coordinate
from apps.routing.domain.route_models import Coordinate


@lru_cache(maxsize=1)
def _finder():
    from timezonefinder import TimezoneFinder

    return TimezoneFinder()


@lru_cache(maxsize=4096)
def timezone_at(coordinate: Coordinate) -> str:
    lon, lat = validate_coordinate(coordinate)
    name = _finder().timezone_at(lng=lon, lat=lat)
    try:
        if name:
            ZoneInfo(name)
            return name
    except (ValueError, ZoneInfoNotFoundError):
        pass
    raise RoutingError("timezone_unavailable", "The time zone could not be determined for a route location.")

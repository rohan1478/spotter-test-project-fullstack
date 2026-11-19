from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class DepartureError(ValueError):
    pass


def normalize_departure(value: datetime, zone_name: str | None) -> datetime:
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value.astimezone(timezone.utc)
    if not zone_name:
        raise DepartureError("Include a UTC offset/Z, or supply departureTimeZone for a local date/time.")
    zone = ZoneInfo(zone_name)
    candidates = set()
    for fold in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        if candidate.astimezone(zone).replace(tzinfo=None) == value:
            candidates.add(candidate)
    if not candidates:
        raise DepartureError("This local time does not exist because of a daylight-saving change. Choose another time.")
    if len(candidates) > 1:
        raise DepartureError("This local time occurs twice because of a daylight-saving change. Include the intended UTC offset.")
    return candidates.pop()

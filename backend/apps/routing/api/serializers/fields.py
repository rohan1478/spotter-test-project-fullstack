import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class StrictSerializer(serializers.Serializer):

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ["Unknown field."] for key in sorted(unknown)})
        return super().to_internal_value(data)


class FiniteFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            raise serializers.ValidationError("Enter a finite number.")
        return value


@extend_schema_field({
    "type": "array", "items": {"type": "number", "format": "double"},
    "minItems": 2, "maxItems": 2,
    "description": "[longitude, latitude], in WGS84 degrees. Longitude: -180..180; latitude: -90..90.",
})
class CoordinateField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=FiniteFloatField(), min_length=2, max_length=2, **kwargs)

    def to_internal_value(self, data):
        coordinate = super().to_internal_value(data)
        if len(coordinate) != 2:
            raise serializers.ValidationError("Supply exactly two values: [longitude, latitude].")
        if not -180 <= coordinate[0] <= 180 or not -90 <= coordinate[1] <= 90:
            raise serializers.ValidationError("Use [longitude, latitude] within [-180..180, -90..90].")
        return coordinate


class TimeZoneField(serializers.CharField):
    def __init__(self, **kwargs):
        super().__init__(max_length=100, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError("Enter a valid IANA time zone, such as America/Chicago.")
        return value


class DepartureField(serializers.DateTimeField):

    def enforce_timezone(self, value):
        return value


class LocationLabelField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", settings.ROUTING_MAX_LOCATION_LENGTH)
        super().__init__(**kwargs)

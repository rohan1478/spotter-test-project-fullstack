from datetime import timedelta

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from shapely.geometry import shape

from apps.routing.domain.choices import RISK_CHOICES, RISK_SCORES
from .fields import CoordinateField, FiniteFloatField, StrictSerializer
from .responses import ForecastMetadataSerializer, WarningSerializer


@extend_schema_field({
    "type": "object", "required": ["type", "coordinates"],
    "properties": {
        "type": {"type": "string", "enum": ["Polygon", "MultiPolygon"]},
        "coordinates": {"type": "array", "items": {"type": "array", "items": {}}},
    },
    "description": "Clipped WGS84 GeoJSON Polygon or MultiPolygon, split at the antimeridian.",
})
class PolygonGeometryField(serializers.JSONField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            geometry = shape(value)
            if geometry.geom_type not in ("Polygon", "MultiPolygon") or geometry.is_empty or not geometry.is_valid:
                raise ValueError("Invalid polygon.")
            west, south, east, north = geometry.bounds
            if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
                raise ValueError("Out-of-range polygon.")
        except (ValueError, TypeError, AttributeError, KeyError):
            raise serializers.ValidationError("Expected valid WGS84 Polygon or MultiPolygon GeoJSON.")
        return value


class CorridorCellSerializer(StrictSerializer):
    id = serializers.CharField()
    coordinate = CoordinateField()
    geometry = PolygonGeometryField()


class CorridorGridSerializer(StrictSerializer):
    bufferMiles = FiniteFloatField(min_value=0)
    requestedSpacingMiles = FiniteFloatField(min_value=0)
    spacingMiles = FiniteFloatField(min_value=0)
    coarsened = serializers.BooleanField()
    cellCount = serializers.IntegerField(min_value=1)
    center = CoordinateField()
    projection = serializers.CharField()
    boundary = PolygonGeometryField()
    cells = CorridorCellSerializer(many=True, min_length=1)

    def validate(self, attrs):
        if len(attrs["cells"]) != attrs["cellCount"]:
            raise serializers.ValidationError({"cellCount": "Must match the number of grid cells."})
        if len({cell["id"] for cell in attrs["cells"]}) != attrs["cellCount"]:
            raise serializers.ValidationError({"cells": "Cell IDs must be unique."})
        return attrs


class CorridorFrameSerializer(StrictSerializer):
    offsetHours = serializers.IntegerField(min_value=0, max_value=48)
    time = serializers.DateTimeField()
    riskScores = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=4, allow_null=True))
    complete = serializers.BooleanField()
    missingCellCount = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        missing = attrs["riskScores"].count(None)
        if missing != attrs["missingCellCount"] or attrs["complete"] != (missing == 0):
            raise serializers.ValidationError("Frame completeness must match its unknown cell scores.")
        return attrs


class RiskLevelSerializer(StrictSerializer):
    score = serializers.IntegerField(min_value=0, max_value=4)
    risk = serializers.ChoiceField(choices=RISK_CHOICES)
    label = serializers.CharField()


class CorridorForecastSerializer(StrictSerializer):
    analysisId = serializers.UUIDField()
    forecastStart = serializers.DateTimeField()
    expiresAt = serializers.DateTimeField()
    complete = serializers.BooleanField()
    grid = CorridorGridSerializer()
    frames = CorridorFrameSerializer(many=True, min_length=49, max_length=49)
    riskLevels = RiskLevelSerializer(many=True, min_length=5, max_length=5)
    forecastMetadata = ForecastMetadataSerializer()
    warnings = WarningSerializer(many=True)

    def validate(self, attrs):
        count = attrs["grid"]["cellCount"]
        for offset, frame in enumerate(attrs["frames"]):
            if frame["offsetHours"] != offset or frame["time"] != attrs["forecastStart"] + timedelta(hours=offset):
                raise serializers.ValidationError({"frames": "Frames must cover consecutive UTC hours 0 through 48."})
            if len(frame["riskScores"]) != count:
                raise serializers.ValidationError({"frames": "Each score array must match the fixed cell order/count."})
        if attrs["complete"] != all(frame["complete"] for frame in attrs["frames"]):
            raise serializers.ValidationError({"complete": "Must reflect all hourly frames."})
        if {item["score"]: item["risk"] for item in attrs["riskLevels"]} != {score: risk.value for risk, score in RISK_SCORES.items()}:
            raise serializers.ValidationError({"riskLevels": "Use the fixed Low=0 through No Travel=4 legend."})
        return attrs

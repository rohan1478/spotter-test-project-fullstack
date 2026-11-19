import math

from rest_framework import serializers

from apps.routing.domain.choices import RISK_CHOICES, WEATHER_STATUS_CHOICES

from .fields import CoordinateField, FiniteFloatField, StrictSerializer, TimeZoneField
from .places import ResolvedPlaceSerializer
from .requests import CompareTripRequestSerializer


class WarningSerializer(StrictSerializer):
    code = serializers.CharField(max_length=100)
    message = serializers.CharField()
    routeId = serializers.CharField(required=False, max_length=100)


class CheckpointSerializer(StrictSerializer):
    id = serializers.CharField(max_length=100)
    number = serializers.IntegerField(min_value=0)
    name = serializers.CharField(max_length=200)
    coordinate = CoordinateField()
    miles = FiniteFloatField(min_value=0)
    arrival = serializers.DateTimeField()
    timeZone = TimeZoneField()
    wind = FiniteFloatField(min_value=0, allow_null=True)
    rain = FiniteFloatField(min_value=0, allow_null=True)
    snow = FiniteFloatField(min_value=0, allow_null=True)
    risk = serializers.ChoiceField(choices=RISK_CHOICES, allow_null=True)
    weatherStatus = serializers.ChoiceField(choices=WEATHER_STATUS_CHOICES)
    elapsedMinutes = FiniteFloatField(min_value=0, required=False)
    forecastTime = serializers.DateTimeField(required=False, allow_null=True)
    riskReasons = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs):
        if attrs["weatherStatus"] == "available" and any(attrs[key] is None for key in ("wind", "rain", "snow", "risk")):
            raise serializers.ValidationError("Available weather must include wind, rain, snow, and risk.")
        if attrs["weatherStatus"] == "missing" and attrs["risk"] is not None:
            raise serializers.ValidationError({"risk": "Missing weather must have null risk."})
        return attrs


class ExposureSerializer(StrictSerializer):
    risk = serializers.ChoiceField(choices=RISK_CHOICES, allow_null=True, help_text="Null identifies miles with unknown weather.")
    miles = FiniteFloatField(min_value=0)


class RouteSegmentSerializer(StrictSerializer):
    id = serializers.CharField(max_length=100)
    geometry = serializers.ListField(child=CoordinateField(), min_length=2)
    startMiles = FiniteFloatField(min_value=0)
    endMiles = FiniteFloatField(min_value=0)
    risk = serializers.ChoiceField(choices=RISK_CHOICES, allow_null=True)

    def validate(self, attrs):
        if attrs["endMiles"] <= attrs["startMiles"]:
            raise serializers.ValidationError({"endMiles": "End miles must be greater than start miles."})
        return attrs


class RouteOptionSerializer(StrictSerializer):
    id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=200)
    highway = serializers.CharField(max_length=200, allow_blank=True)
    distance = FiniteFloatField(min_value=0, help_text="Total distance in miles.")
    duration = FiniteFloatField(min_value=0, help_text="Total duration in minutes.")
    risk = serializers.ChoiceField(choices=RISK_CHOICES, allow_null=True)
    severeMiles = FiniteFloatField(min_value=0)
    highMiles = FiniteFloatField(min_value=0)
    noTravelMiles = FiniteFloatField(min_value=0)
    unknownMiles = FiniteFloatField(min_value=0)
    averageRisk = FiniteFloatField(min_value=0, max_value=4, allow_null=True)
    recommended = serializers.BooleanField()
    eligible = serializers.BooleanField()
    complete = serializers.BooleanField()
    explanation = serializers.CharField()
    geometry = serializers.ListField(child=CoordinateField(), min_length=2)
    checkpoints = CheckpointSerializer(many=True, min_length=2)
    exposure = ExposureSerializer(many=True, min_length=1)
    segments = RouteSegmentSerializer(many=True, min_length=1)
    providerDistance = FiniteFloatField(min_value=0, required=False)
    routingProfile = serializers.CharField(required=False)
    avoid = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs):
        if not math.isclose(sum(item["miles"] for item in attrs["exposure"]), attrs["distance"], abs_tol=0.01):
            raise serializers.ValidationError({"exposure": "Exposure miles must sum to the route distance."})
        if attrs["complete"] and (
            any(point["weatherStatus"] != "available" for point in attrs["checkpoints"])
            or any(segment["risk"] is None for segment in attrs["segments"])
            or attrs["unknownMiles"] > 0
            or attrs["risk"] is None
            or attrs["averageRisk"] is None
        ):
            raise serializers.ValidationError({"complete": "Complete routes must have all required weather and risk values."})
        if attrs["eligible"] and (not attrs["complete"] or attrs["noTravelMiles"] > 0 or attrs["unknownMiles"] > 0):
            raise serializers.ValidationError({"eligible": "Incomplete routes and routes with No Travel miles are ineligible."})
        if attrs["recommended"] and not attrs["eligible"]:
            raise serializers.ValidationError({"recommended": "An ineligible route cannot be recommended."})
        if not attrs["complete"] and (attrs["risk"] is not None or attrs["averageRisk"] is not None):
            raise serializers.ValidationError("Incomplete routes must use null overall risk and averageRisk.")
        return attrs


class ResolvedPlacesSerializer(StrictSerializer):
    origin = ResolvedPlaceSerializer()
    destination = ResolvedPlaceSerializer()


class ForecastUnitsSerializer(StrictSerializer):
    wind = serializers.ChoiceField(choices=["mph"])
    rain = serializers.ChoiceField(choices=["in/hr"])
    snow = serializers.ChoiceField(choices=["in/hr"])


class ForecastMetadataSerializer(StrictSerializer):
    provider = serializers.CharField()
    retrievedAt = serializers.DateTimeField()
    startsAt = serializers.DateTimeField()
    endsAt = serializers.DateTimeField()
    stepHours = serializers.ChoiceField(choices=[1])
    units = ForecastUnitsSerializer()
    attribution = serializers.CharField(required=False)
    windSampling = serializers.CharField(required=False)
    precipitationSampling = serializers.CharField(required=False)

    def validate(self, attrs):
        if attrs["endsAt"] <= attrs["startsAt"]:
            raise serializers.ValidationError({"endsAt": "Forecast end must follow forecast start."})
        return attrs


class TripResultSerializer(StrictSerializer):
    analysisId = serializers.UUIDField()
    expiresAt = serializers.DateTimeField()
    routes = RouteOptionSerializer(many=True, max_length=3)
    trip = CompareTripRequestSerializer()
    resolvedPlaces = ResolvedPlacesSerializer()
    forecastStart = serializers.DateTimeField(help_text="UTC analysis hour anchoring the corridor slider's 0–48h window.")
    forecastMetadata = ForecastMetadataSerializer()
    recommendedRouteId = serializers.CharField(allow_null=True, max_length=100)
    warnings = WarningSerializer(many=True)
    recommendationReason = serializers.CharField(required=False)
    rankedRouteIds = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs):
        ids = [route["id"] for route in attrs["routes"]]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError({"routes": "Route IDs must be unique."})
        recommended = [route["id"] for route in attrs["routes"] if route["recommended"]]
        expected = [] if attrs["recommendedRouteId"] is None else [attrs["recommendedRouteId"]]
        if recommended != expected:
            raise serializers.ValidationError({"recommendedRouteId": "Must match the single recommended route, or be null when none qualifies."})
        return attrs

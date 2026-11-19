from rest_framework import serializers

from .fields import CoordinateField, FiniteFloatField, StrictSerializer, TimeZoneField
from .places import ResolvedPlaceSerializer
from .responses import ResolvedPlacesSerializer, WarningSerializer


class PlaceSearchRequestSerializer(StrictSerializer):
    q = serializers.CharField(min_length=2, max_length=200)
    limit = serializers.IntegerField(min_value=1, max_value=5, default=5)


class PlaceSearchResponseSerializer(StrictSerializer):
    results = ResolvedPlaceSerializer(many=True)
    requiresSelection = serializers.BooleanField()
    attribution = serializers.CharField()


class RouteCheckpointSerializer(StrictSerializer):
    id = serializers.CharField()
    number = serializers.IntegerField(min_value=0)
    name = serializers.CharField()
    coordinate = CoordinateField()
    miles = FiniteFloatField(min_value=0)
    arrival = serializers.DateTimeField()
    timeZone = TimeZoneField()
    elapsedMinutes = FiniteFloatField(min_value=0)


class UnscoredRouteSerializer(StrictSerializer):
    id = serializers.CharField()
    name = serializers.CharField()
    highway = serializers.CharField(allow_blank=True)
    geometry = serializers.ListField(child=CoordinateField(), min_length=2)
    distance = FiniteFloatField(min_value=0, help_text="WGS84 road-geometry distance in miles.")
    providerDistance = FiniteFloatField(min_value=0, help_text="Original Mapbox distance in miles, retained separately.")
    duration = FiniteFloatField(min_value=0, help_text="Provider route duration in minutes.")
    routingProfile = serializers.ChoiceField(choices=["mapbox/driving"])
    avoid = serializers.ListField(child=serializers.ChoiceField(choices=["toll", "motorway"]))
    checkpoints = RouteCheckpointSerializer(many=True, min_length=2)


class RouteOptionsSerializer(StrictSerializer):
    routes = UnscoredRouteSerializer(many=True, min_length=1, max_length=3)
    resolvedPlaces = ResolvedPlacesSerializer()
    departure = serializers.DateTimeField()
    spacing = serializers.ChoiceField(choices=[10, 25, 50])
    distanceBasis = serializers.ChoiceField(choices=["wgs84-geodesic"])
    warnings = WarningSerializer(many=True)

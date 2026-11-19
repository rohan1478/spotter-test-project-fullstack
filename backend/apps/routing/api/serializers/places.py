from rest_framework import serializers

from .fields import CoordinateField, LocationLabelField, StrictSerializer, TimeZoneField


class ResolvedPlaceSerializer(StrictSerializer):
    id = serializers.CharField(max_length=200, help_text="Provider's opaque location identifier.")
    label = LocationLabelField()
    coordinate = CoordinateField()
    timeZone = TimeZoneField()

from django.conf import settings
from rest_framework import serializers

from apps.routing.domain.departure import DepartureError, normalize_departure

from .fields import DepartureField, FiniteFloatField, LocationLabelField, StrictSerializer, TimeZoneField
from .places import ResolvedPlaceSerializer


class CompareTripRequestSerializer(StrictSerializer):
    origin = LocationLabelField()
    destination = LocationLabelField()
    departure = DepartureField(help_text="ISO 8601 with UTC offset/Z; local times need an explicit IANA zone.")
    departureTimeZone = TimeZoneField(required=False)
    loadWeight = FiniteFloatField(min_value=0, max_value=settings.ROUTING_MAX_LOAD_LB, help_text="Positive load weight in pounds; application maximum is configurable.")
    spacing = serializers.ChoiceField(choices=[10, 25, 50])
    originPlace = ResolvedPlaceSerializer(required=False)
    destinationPlace = ResolvedPlaceSerializer(required=False)

    def validate_loadWeight(self, value):
        if not 0 < value <= settings.ROUTING_MAX_LOAD_LB:
            raise serializers.ValidationError(f"Enter a load greater than 0 and no more than {settings.ROUTING_MAX_LOAD_LB:,} lb.")
        return value

    def validate(self, attrs):
        origin_place = attrs.get("originPlace")
        destination_place = attrs.get("destinationPlace")
        if bool(origin_place) != bool(destination_place):
            raise serializers.ValidationError({"originPlace": "Supply both resolved places, or neither."})
        if attrs["origin"].casefold() == attrs["destination"].casefold():
            raise serializers.ValidationError({"destination": "Origin and destination must differ."})
        if origin_place and origin_place["coordinate"] == destination_place["coordinate"]:
            raise serializers.ValidationError({"destinationPlace": "Origin and destination coordinates must differ."})
        zone = attrs.get("departureTimeZone")
        if origin_place:
            if zone and zone != origin_place["timeZone"]:
                raise serializers.ValidationError({"departureTimeZone": "Use the resolved origin's time zone."})
            zone = origin_place["timeZone"]
        try:
            attrs["departure"] = normalize_departure(attrs["departure"], zone)
        except DepartureError as exc:
            raise serializers.ValidationError({"departure": str(exc)})
        return attrs

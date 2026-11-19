from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.serializers import ErrorResponseSerializer
from apps.routing.domain.errors import RoutingError
from apps.routing.services.routes import get_route_options, search_places
from apps.routing.services.comparison import compare_routes

from .exceptions import RoutingAPIError
from .serializers import CompareTripRequestSerializer, TripResultSerializer
from .serializers.options import (
    PlaceSearchRequestSerializer,
    PlaceSearchResponseSerializer,
    RouteOptionsSerializer,
)


class PlaceSearchView(APIView):
    @extend_schema(
        tags=["Locations"], summary="Search for origin/destination choices",
        parameters=[PlaceSearchRequestSerializer],
        responses={200: PlaceSearchResponseSerializer, 400: ErrorResponseSerializer,
                   502: ErrorResponseSerializer, 503: ErrorResponseSerializer, 504: ErrorResponseSerializer},
    )
    def get(self, request):
        serializer = PlaceSearchRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            result = search_places(serializer.validated_data["q"], serializer.validated_data["limit"])
        except RoutingError as error:
            raise RoutingAPIError(error) from None
        return Response(PlaceSearchResponseSerializer(result).data)


class RouteOptionsView(APIView):
    @extend_schema(
        tags=["Routes"], summary="Get unscored routes, checkpoints, and arrival times",
        description=(
            "Phase 3 endpoint: real driving routes and ETAs without weather or recommendations. "
            "Text locations with multiple matches require explicit selection (409). "
            "At most three Mapbox requests generate distinct routes; extra candidates may avoid "
            "tolls or motorways as recorded in each route's avoid list."
        ),
        request=CompareTripRequestSerializer,
        responses={200: RouteOptionsSerializer, 400: ErrorResponseSerializer,
                   409: ErrorResponseSerializer, 413: ErrorResponseSerializer, 415: ErrorResponseSerializer,
                   422: ErrorResponseSerializer, 502: ErrorResponseSerializer,
                   503: ErrorResponseSerializer, 504: ErrorResponseSerializer},
    )
    def post(self, request):
        serializer = CompareTripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = get_route_options(serializer.validated_data)
        except RoutingError as error:
            raise RoutingAPIError(error) from None
        return Response(RouteOptionsSerializer(result).data)


class CompareRoutesView(APIView):
    @extend_schema(
        tags=["Routes"],
        summary="Compare driving routes using checkpoint arrival-time weather",
        description=(
            "Retrieve real routes and hourly Open-Meteo forecasts at checkpoint ETAs. "
            "Rank complete routes without No Travel exposure by Severe miles, High miles, "
            "distance-weighted average risk, then duration. Incomplete routes remain visible "
            "but cannot be recommended. Dates outside the forecast window return 422."
        ),
        request=CompareTripRequestSerializer,
        responses={
            200: OpenApiResponse(TripResultSerializer, description="Routes with arrival forecasts, risk exposure, and an optional recommendation."),
            400: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
            415: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
            502: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
            504: ErrorResponseSerializer,
        },
        examples=[OpenApiExample("Offset-aware trip", request_only=True, value={
            "origin": "Chicago, IL", "destination": "Indianapolis, IN",
            "departure": "2026-11-19T08:00:00-06:00", "loadWeight": 32000, "spacing": 25,
        })],
    )
    def post(self, request):
        serializer = CompareTripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = compare_routes(serializer.validated_data)
        except RoutingError as error:
            raise RoutingAPIError(error) from None
        return Response(TripResultSerializer(result).data)

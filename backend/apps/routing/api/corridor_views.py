from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.serializers import ErrorResponseSerializer
from apps.routing.domain.errors import RoutingError
from apps.routing.services.corridor import get_corridor_forecast

from .exceptions import RoutingAPIError
from .serializers.corridor import CorridorForecastSerializer


class CorridorForecastView(APIView):
    @extend_schema(
        tags=["Forecast"], summary="Get 49 cached corridor forecast frames (0–48 hours)",
        description=(
            "Use analysisId from a recent comparison. Returns clipped grid geometry once and "
            "fixed-order risk-score arrays per hour. Scores use the same 0–4 scale at every "
            "grid resolution; null means unknown. An expired/evicted analysis returns 410."
        ),
        responses={200: CorridorForecastSerializer, 409: ErrorResponseSerializer,
                   410: ErrorResponseSerializer, 422: ErrorResponseSerializer,
                   502: ErrorResponseSerializer, 503: ErrorResponseSerializer, 504: ErrorResponseSerializer},
    )
    def get(self, request, analysis_id):
        try:
            result = get_corridor_forecast(analysis_id)
        except RoutingError as error:
            raise RoutingAPIError(error) from None
        return Response(CorridorForecastSerializer(result).data)

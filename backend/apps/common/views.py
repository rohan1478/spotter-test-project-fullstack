from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .exceptions import error_body
from .serializers import HealthSerializer


@extend_schema(responses=HealthSerializer, auth=[], tags=["Health"], description="Process liveness only; does not call providers or check forecast availability.")
@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "weather-aware-routing", "version": "0.1.0"})


def bad_request(request, exception):
    return JsonResponse(error_body("bad_request", "The request could not be processed."), status=400)


def not_found(request, exception):
    return JsonResponse(error_body("not_found", "The requested endpoint does not exist."), status=404)


def server_error(request):
    return JsonResponse(error_body("internal_error", "An unexpected server error occurred."), status=500)

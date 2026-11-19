from django.conf import settings
from django.http import JsonResponse

from .exceptions import error_body


class ApiRequestMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        content_length = request.META.get("CONTENT_LENGTH", "")
        if content_length:
            try:
                length = int(content_length)
            except ValueError:
                return JsonResponse(error_body("invalid_content_length", "Invalid Content-Length header."), status=400)
            if length < 0:
                return JsonResponse(error_body("invalid_content_length", "Invalid Content-Length header."), status=400)
            if length > settings.API_MAX_REQUEST_BYTES:
                return JsonResponse(error_body("request_too_large", "The request body exceeds the allowed size."), status=413)
        response = self.get_response(request)
        if response.status_code == 404 and not response.get("Content-Type", "").startswith("application/json"):
            return JsonResponse(error_body("not_found", "The requested endpoint does not exist."), status=404)
        return response

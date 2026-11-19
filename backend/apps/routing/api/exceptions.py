from rest_framework.exceptions import APIException

from apps.routing.domain.errors import RoutingError

STATUS_CODES = {
    "ambiguous_location": 409,
    "location_not_found": 422,
    "location_timezone_mismatch": 422,
    "identical_locations": 422,
    "no_route": 422,
    "timezone_unavailable": 422,
    "too_many_checkpoints": 422,
    "too_many_weather_locations": 422,
    "forecast_out_of_range": 422,
    "forecast_expired": 503,
    "analysis_expired": 410,
    "corridor_in_progress": 409,
    "corridor_too_large": 422,
    "invalid_corridor_geometry": 422,
    "provider_not_configured": 503,
    "provider_rate_limited": 503,
    "provider_timeout": 504,
    "provider_authentication_error": 502,
    "provider_rejected_request": 502,
    "invalid_provider_response": 502,
    "provider_unavailable": 502,
}


class RoutingAPIError(APIException):
    def __init__(self, error: RoutingError):
        self.status_code = STATUS_CODES.get(error.code, 502)
        self.default_code = error.code
        self.context_details = error.details
        super().__init__(detail=error.message, code=error.code)

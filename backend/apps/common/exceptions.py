import logging

from django.core.exceptions import RequestDataTooBig
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def error_body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def api_exception_handler(exc, context):
    if isinstance(exc, RequestDataTooBig):
        return Response(error_body("request_too_large", "The request body exceeds the allowed size."), status=413)
    response = exception_handler(exc, context)
    if response is None:
        logger.error("Unhandled API error", exc_info=(type(exc), exc, exc.__traceback__))
        return Response(error_body("internal_error", "An unexpected server error occurred."), status=500)
    if response.status_code == 400 and not isinstance(response.data, dict):
        details = {"nonFieldErrors": response.data}
    else:
        details = response.data
    code = getattr(exc, "default_code", "request_error")
    if response.status_code == 422:
        logger.warning("API request rejected: status=422 code=%s", code)
    if response.status_code == 400 and code == "invalid":
        code = "validation_error"
    message = "Check the highlighted request fields."
    if isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])
        details = getattr(exc, "context_details", {})
    response.data = error_body(code, message, details)
    return response

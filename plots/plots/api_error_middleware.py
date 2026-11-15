import logging

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger("django.request")


class ApiErrorMiddleware(MiddlewareMixin):
    """Return safe JSON for uncaught API exceptions and log the real failure."""

    def process_exception(self, request, exception):
        if request.path != "/api" and not request.path.startswith("/api/"):
            return None

        logger.exception(
            "Unhandled API exception for %s %s",
            request.method,
            request.path,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        return JsonResponse(
            {"detail": "An unexpected server error occurred. Please try again later."},
            status=500,
        )

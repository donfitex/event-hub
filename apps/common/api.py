from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.renderers import JSONRenderer
from rest_framework.views import exception_handler as drf_handler
from rest_framework.response import Response


class EnvelopeRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response and response.status_code < 400 and data is not None:
            data = {"data": data}
        return super().render(data, accepted_media_type, renderer_context)


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input.",
                    "details": exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
                }
            },
            status=400,
        )
    response = drf_handler(exc, context)
    if response is not None:
        details = response.data
        code = getattr(
            exc,
            "default_code",
            {
                404: "not_found",
                403: "permission_denied",
                401: "not_authenticated",
                429: "rate_limited",
                400: "validation_error",
            }.get(response.status_code, "error"),
        )
        if hasattr(exc, "get_codes") and isinstance(exc.get_codes(), str):
            code = exc.get_codes()
        response.data = {
            "error": {
                "code": code.upper(),
                "message": str(details.get("detail", "Invalid input."))
                if isinstance(details, dict)
                else "Invalid input.",
                "details": details,
            }
        }
    return response

from django.conf import settings


def deployment(request):
    return {
        "preview_mode": settings.PREVIEW_MODE,
        "image_uploads_enabled": settings.EVENT_IMAGE_UPLOADS_ENABLED,
    }

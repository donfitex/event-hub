from django.conf import settings


def deployment(request):
    return {"preview_mode": settings.PREVIEW_MODE}

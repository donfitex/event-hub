from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token.created + timedelta(days=settings.API_TOKEN_TTL_DAYS) <= timezone.now():
            token.delete()
            raise AuthenticationFailed("Token expired. Please log in again.")
        return user, token

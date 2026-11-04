from drf_spectacular.extensions import OpenApiAuthenticationExtension


class NeonScheme(OpenApiAuthenticationExtension):
    target_class = "apps.users.neon.NeonAuthentication"
    name = "neonBearer"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Neon Managed Better Auth JWT; EdDSA, issuer and expiry verified.",
        }


class ExpiringScheme(OpenApiAuthenticationExtension):
    target_class = "apps.users.authentication.ExpiringTokenAuthentication"
    name = "expiringToken"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Token <key>, expires after 14 days. Local identity mode only.",
        }

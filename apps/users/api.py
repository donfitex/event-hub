from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import User
from .security import login_attempt


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_organizer"]
        read_only_fields = ["id", "email", "is_organizer"]


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name"]
        read_only_fields = ["id"]

    def create(self, data):
        return User.objects.create_user(**data)


class Signup(generics.CreateAPIView):
    def create(self, request, *args, **kwargs):
        if settings.NEON_AUTH_BASE_URL:
            return Response(
                {
                    "error": {
                        "code": "MANAGED_AUTH",
                        "message": "Use Neon Better Auth sign-up and a Bearer JWT.",
                    }
                },
                status=400,
            )
        return super().create(request, *args, **kwargs)

    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "signup"


class Login(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    serializer_class = SignupSerializer

    def post(self, request):
        if settings.NEON_AUTH_BASE_URL:
            return Response(
                {
                    "error": {
                        "code": "MANAGED_AUTH",
                        "message": "Use Neon Better Auth sign-in and a Bearer JWT.",
                    }
                },
                status=400,
            )
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        if not isinstance(email, str) or not isinstance(password, str):
            raise serializers.ValidationError("Email and password must be strings.")
        user, error = login_attempt(request, email, password)
        if error:
            return Response(
                {"error": {"code": "LOGIN_FAILED", "message": error}},
                status=429 if error.startswith("Too many") else 400,
            )
        token, _ = Token.objects.get_or_create(user=user)
        if token.created + timedelta(days=14) <= timezone.now():
            token.delete()
            token = Token.objects.create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class Logout(APIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        from django.contrib.auth import logout

        logout(request)
        return Response(status=204)


class Profile(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AdminUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["is_active"]
        read_only_fields = ["id", "email"]


class ManageUsers(generics.ListAPIView):
    queryset = User.objects.order_by("pk")
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]


class ManageUser(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]

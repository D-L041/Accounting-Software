from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SchoolMembership


def user_payload(user):
    memberships = SchoolMembership.objects.filter(
        user=user, is_active=True, school__is_active=True
    ).select_related("school").order_by("school__name")
    return {
        "id": user.pk,
        "username": user.get_username(),
        "name": user.get_full_name() or user.get_username(),
        "schools": [
            {
                "id": item.school_id,
                "name": item.school.name,
                "code": item.school.code,
                "currency": item.school.currency,
                "role": item.role,
            }
            for item in memberships
        ],
    }


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")
        if not username or not password:
            return Response({"detail": "Enter your username and password."}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return Response({"detail": "The username or password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({"user": user_payload(user)})


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"user": user_payload(request.user)})


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

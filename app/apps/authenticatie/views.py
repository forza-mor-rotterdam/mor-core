import logging

from apps.authenticatie.serializers import GebruikerSerializer
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class LoginView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return redirect("/admin/")
        if request.user.is_authenticated:
            return redirect(reverse("root"), False)

        if settings.OIDC_ENABLED:
            return redirect(f"/oidc/authenticate/?next={request.GET.get('next', '/')}")
        if settings.ENABLE_DJANGO_ADMIN_LOGIN:
            return redirect(f"/admin/login/?next={request.GET.get('next', '/admin')}")

        return HttpResponse("Er is geen login ingesteld")


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse("login"), False)

        if settings.OIDC_ENABLED:
            return redirect("/oidc/logout/")
        if settings.ENABLE_DJANGO_ADMIN_LOGIN:
            return redirect(f"/admin/logout/?next={request.GET.get('next', '/')}")

        return HttpResponse("Er is geen logout ingesteld")


class GetGebruikerAPIView(APIView):
    serializer_class = GebruikerSerializer

    def get(self, request, email=None):
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"email": "is not a valid email address"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cache_gebruiker = cache.get(f"gebruiker_{email}", {})
        cache_gebruiker.update({"email": email})
        gebruiker_serializer = GebruikerSerializer(data=cache_gebruiker)
        if gebruiker_serializer.is_valid():
            return Response(
                gebruiker_serializer.validated_data, status=status.HTTP_200_OK
            )
        return Response(gebruiker_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SetGebruikerAPIView(APIView):
    serializer_class = GebruikerSerializer

    def post(self, request):
        serializer = GebruikerSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            cache.set(
                f"gebruiker_{serializer.data.get('email')}",
                serializer.validated_data,
                timeout=None,
            )
            return Response({}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

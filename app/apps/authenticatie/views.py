import logging

from apps.authenticatie.serializers import GebruikerSerializer
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


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

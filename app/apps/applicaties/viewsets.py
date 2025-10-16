from apps.applicaties.models import Applicatie
from apps.applicaties.serializers import TaakapplicatieSerializer
from rest_framework import viewsets


class TaakapplicatieViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Taakapplicaties voor MOR
    """

    queryset = Applicatie.objects.all()

    serializer_class = TaakapplicatieSerializer
    lookup_field = "uuid"

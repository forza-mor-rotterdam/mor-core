from apps.applicaties.filtersets import ApplicatieFilterSet
from apps.applicaties.models import Applicatie
from apps.applicaties.serializers import TaakapplicatieSerializer
from django_filters import rest_framework as filters
from rest_framework import viewsets


class TaakapplicatieViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Taakapplicaties voor MOR
    """

    queryset = Applicatie.objects.all()

    serializer_class = TaakapplicatieSerializer
    lookup_field = "uuid"

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ApplicatieFilterSet

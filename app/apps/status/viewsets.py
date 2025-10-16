import logging

from apps.status.filtersets import RelatedOrderingFilter, StatusFilter
from apps.status.models import Status
from apps.status.serializers import (
    StatusAfgehandeldSerializer,
    StatusLijstSerializer,
    StatusVeranderingSerializer,
)
from config.context import db
from django.conf import settings
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class StatusViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = Status.objects.all()

    serializer_class = StatusLijstSerializer
    filter_backends = (
        filters.DjangoFilterBackend,
        RelatedOrderingFilter,
    )
    ordering_fields = "__all_related__"
    filterset_class = StatusFilter

    @extend_schema(
        description="Unieke status verandering duur per wijk en onderwerp",
        responses={status.HTTP_200_OK: StatusVeranderingSerializer(many=True)},
        parameters=None,
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="veranderingen",
        serializer_class=StatusVeranderingSerializer,
    )
    def veranderingen(self, request):
        with db(settings.READONLY_DATABASE_KEY):
            serializer = StatusVeranderingSerializer(
                self.filter_queryset(self.get_queryset()).veranderingen(request.GET),
                context={"request": request},
                many=True,
            )
        return Response(serializer.data)

    @extend_schema(
        description="Doorlooptijden afgehandelde meldingen",
        responses={status.HTTP_200_OK: StatusAfgehandeldSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                "aangemaakt_op_gte",
                OpenApiTypes.DATETIME,
                OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                "aangemaakt_op_lt",
                OpenApiTypes.DATETIME,
                OpenApiParameter.QUERY,
            ),
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="afgehandeld",
        serializer_class=StatusAfgehandeldSerializer,
    )
    def afgehandeld(self, request):
        with db(settings.READONLY_DATABASE_KEY):
            serializer = StatusAfgehandeldSerializer(
                self.get_queryset().doorlooptijden_afgehandelde_meldingen(request.GET),
                context={"request": request},
                many=True,
            )
            response = Response(serializer.data)
        return response

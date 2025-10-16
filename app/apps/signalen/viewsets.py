import logging

from apps.meldingen.models import Melding
from apps.signalen.filtersets import RelatedOrderingFilter, SignaalFilter
from apps.signalen.models import Signaal
from apps.signalen.serializers import (
    SignaalAantallenSerializer,
    SignaalListSerializer,
    SignaalSerializer,
)
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@extend_schema(
    parameters=[
        OpenApiParameter("signaal_url", OpenApiTypes.URI, OpenApiParameter.QUERY),
        OpenApiParameter("ordering", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter(
            "melding__origineel_aangemaakt_gte",
            OpenApiTypes.DATETIME,
            OpenApiParameter.QUERY,
        ),
    ]
)
class SignaalViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = Signaal.objects.all()

    serializer_class = SignaalSerializer
    serializer_list_class = SignaalListSerializer

    filter_backends = (
        filters.DjangoFilterBackend,
        RelatedOrderingFilter,
    )
    ordering_fields = "__all_related__"
    filterset_class = SignaalFilter

    def get_serializer_class(self):
        if self.action == "list":
            return self.serializer_list_class
        return super().get_serializer_class()

    def create(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            signaal = Melding.acties.signaal_aanmaken(serializer)
            serializer = self.serializer_class(signaal, context={"request": request})
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        logger.error(f"Signaal create serializer: errors={serializer.errors}")
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Signaal aantallen per wijk en onderwerp",
        responses={status.HTTP_200_OK: SignaalAantallenSerializer(many=True)},
        parameters=None,
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="aantallen",
        serializer_class=SignaalAantallenSerializer,
    )
    def aantallen(self, request):
        serializer = SignaalAantallenSerializer(
            self.filter_queryset(self.get_queryset()).get_aantallen(),
            context={"request": request},
            many=True,
        )
        return Response(serializer.data)

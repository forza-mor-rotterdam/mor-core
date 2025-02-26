from apps.locatie.models import Locatie
from apps.locatie.serializers import BuurtWijkSerializer
from config.context import db
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class LocatieViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "uuid"
    queryset = Locatie.objects.all()
    serializer_class = BuurtWijkSerializer
    pagination_class = None

    def list(self, request):
        return []

    @extend_schema(
        description="Alle unieke buurten met wijken gesorteert op wijk en buurt",
        responses={status.HTTP_200_OK: BuurtWijkSerializer(many=True)},
        parameters=None,
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="buurten-met-wijken",
        serializer_class=BuurtWijkSerializer,
    )
    def buurten_met_wijken(self, request):
        with db(settings.READONLY_DATABASE_KEY):
            queryset = (
                self.filter_queryset(self.get_queryset())
                .filter(
                    primair=True,
                    buurtnaam__isnull=False,
                    wijknaam__isnull=False,
                )
                .values("buurtnaam", "wijknaam")
                .distinct()
                .order_by("wijknaam", "buurtnaam")
            )

            return Response(
                BuurtWijkSerializer(
                    queryset,
                    context={"request": request},
                    many=True,
                ).data
            )

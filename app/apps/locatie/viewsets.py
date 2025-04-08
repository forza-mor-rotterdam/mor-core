from apps.locatie.models import Locatie
from apps.locatie.serializers import BuurtWijkSerializer
from config.context import db
from django.conf import settings
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# from django.db import connection


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


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
        url_path="buurten",
        serializer_class=BuurtWijkSerializer,
    )
    def buurten_met_wijken(self, request):
        with db(settings.READONLY_DATABASE_KEY):
            queryset = (
                self.filter_queryset(self.get_queryset())
                .filter(
                    buurtnaam__isnull=False,
                    wijknaam__isnull=False,
                    plaatsnaam__isnull=False,
                )
                .exclude(Q(buurtnaam="") | Q(wijknaam="") | Q(plaatsnaam=""))
                .values("buurtnaam", "wijknaam", "plaatsnaam")
                .distinct()
                .order_by("plaatsnaam", "wijknaam", "buurtnaam")
            )

            # raw_sql_distinct = 'SELECT DISTINCT "locatie_locatie"."buurtnaam", "locatie_locatie"."wijknaam", "locatie_locatie"."plaatsnaam" FROM "locatie_locatie" WHERE ("locatie_locatie"."buurtnaam" IS NOT NULL AND "locatie_locatie"."plaatsnaam" IS NOT NULL AND "locatie_locatie"."wijknaam" IS NOT NULL) ORDER BY "locatie_locatie"."plaatsnaam" ASC, "locatie_locatie"."wijknaam" ASC, "locatie_locatie"."buurtnaam" ASC'
            # raw_sql = 'SELECT "locatie_locatie"."buurtnaam", "locatie_locatie"."wijknaam", "locatie_locatie"."plaatsnaam" FROM "locatie_locatie" WHERE ("locatie_locatie"."buurtnaam" IS NOT NULL AND "locatie_locatie"."plaatsnaam" IS NOT NULL AND "locatie_locatie"."wijknaam" IS NOT NULL) GROUP BY ("locatie_locatie"."buurtnaam", "locatie_locatie"."wijknaam", "locatie_locatie"."plaatsnaam") ORDER BY "locatie_locatie"."plaatsnaam" ASC, "locatie_locatie"."wijknaam" ASC, "locatie_locatie"."buurtnaam" ASC'
            # with connection.cursor() as c:
            #     c.execute(raw_sql)
            #     queryset = dictfetchall(c)

            return Response(
                BuurtWijkSerializer(
                    queryset,
                    context={"request": request},
                    many=True,
                ).data
            )

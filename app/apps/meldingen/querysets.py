import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models
from django.db import connections
from django.db.models import Count, F, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone

logger = logging.getLogger(__name__)


class MeldingQuerySet(QuerySet):
    def dictfetchall(self, cursor):
        """
        Return all rows from a cursor as a dict.
        Assume the column names are unique.
        """
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def melding_status_buurt_aantallen(self, spoed_start=0, spoed_end=1.1):
        spoed_qs = ""
        if isinstance(spoed_start, (float | int)) and isinstance(
            spoed_end, (float | int)
        ):
            spoed_qs = f'AND "meldingen_melding"."urgentie" >= {float(spoed_start)} AND "meldingen_melding"."urgentie" < {float(spoed_end)}'

        sql = f'SELECT "status_status"."naam", \
            "locatie_locatie"."wijknaam", \
            "locatie_locatie"."buurtnaam", \
            COUNT("status_status"."naam") AS "count" \
            FROM "status_status" \
                JOIN "meldingen_melding" ON ("status_status"."id" = "meldingen_melding"."status_id") \
                JOIN "locatie_locatie" ON ("locatie_locatie"."id" = "meldingen_melding"."referentie_locatie_id") \
            WHERE \
                "locatie_locatie"."buurtnaam" IS NOT NULL \
                {spoed_qs} \
            GROUP BY "status_status"."naam", "locatie_locatie"."wijknaam", "locatie_locatie"."buurtnaam" \
            ORDER BY "status_status"."naam", "locatie_locatie"."wijknaam", "locatie_locatie"."buurtnaam" ASC; \
        '
        melding_status_buurt_aantallen_results = []
        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute(sql)
            melding_status_buurt_aantallen_results = self.dictfetchall(cursor)
        return melding_status_buurt_aantallen_results

    def melding_afgehandeld_per_buurt_aantallen(
        self, afgesloten_op_gt, afgesloten_op_lte
    ):
        try:
            afgesloten_op_gt = afgesloten_op_gt.isoformat()
        except Exception:
            afgesloten_op_gt = (timezone.now() - timedelta(hours=24)).isoformat()

        sq_where_to = ""
        try:
            sq_where_to = f'AND "meldingen_melding"."afgesloten_op" <= \'{afgesloten_op_lte.isoformat()}\''
        except Exception:
            ...

        sql = f'SELECT "locatie_locatie"."wijknaam", \
            "locatie_locatie"."buurtnaam", \
            COUNT(*) AS "count" \
            FROM "meldingen_melding" \
                JOIN "locatie_locatie" ON ("locatie_locatie"."id" = "meldingen_melding"."referentie_locatie_id") \
            WHERE \
                "meldingen_melding"."afgesloten_op" > \'{afgesloten_op_gt}\' \
                {sq_where_to} \
            GROUP BY "locatie_locatie"."wijknaam", "locatie_locatie"."buurtnaam" \
            ORDER BY "locatie_locatie"."wijknaam", "locatie_locatie"."buurtnaam" ASC; \
        '
        melding_status_buurt_aantallen_results = []
        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute(sql)
            melding_status_buurt_aantallen_results = self.dictfetchall(cursor)
        return melding_status_buurt_aantallen_results

    def melding_aangemaakt_per_buurt_aantallen(
        self, aangemaakt_op_gt, aangemaakt_op_lte, openstaand=True
    ):
        try:
            aangemaakt_op_gt = aangemaakt_op_gt.isoformat()
        except Exception:
            aangemaakt_op_gt = (timezone.now() - timedelta(hours=24)).isoformat()

        sq_where_to = ""
        try:
            sq_where_to = f'AND "meldingen_melding"."aangemaakt_op" <= \'{aangemaakt_op_lte.isoformat()}\''
        except Exception:
            ...

        sq_openstaand = ""
        if openstaand:
            sq_openstaand = 'AND "meldingen_melding"."afgesloten_op" IS NULL'

        sql = f'SELECT "locatie_locatie"."wijknaam", \
            "locatie_locatie"."buurtnaam", \
            COUNT(*) AS "count" \
            FROM "meldingen_melding" \
                JOIN "locatie_locatie" ON ("locatie_locatie"."id" = "meldingen_melding"."referentie_locatie_id") \
            WHERE \
                "meldingen_melding"."aangemaakt_op" > \'{aangemaakt_op_gt}\' \
                {sq_where_to} \
                {sq_openstaand} \
            GROUP BY "locatie_locatie"."wijknaam", "locatie_locatie"."buurtnaam" \
            ORDER BY "locatie_locatie"."wijknaam", "locatie_locatie"."buurtnaam" ASC; \
        '
        melding_status_buurt_aantallen_results = []
        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute(sql)
            melding_status_buurt_aantallen_results = self.dictfetchall(cursor)
        return melding_status_buurt_aantallen_results

    def nieuwe_meldingen(self):
        from apps.aliassen.models import OnderwerpAlias

        onderwerpen = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("pk")
        )
        meldingen = self.all()

        meldingen = meldingen.annotate(
            onderwerp_naam=Coalesce(
                Subquery(onderwerpen.values("response_json__name")[:1]),
                Value("Onbekend", output_field=models.JSONField()),
            )
        ).annotate(
            wijk=Coalesce(
                F("referentie_locatie__wijknaam"),
                Value("Onbekend"),
            )
        )
        meldingen = meldingen.annotate(
            onderwerp_wijk=Concat(
                "onderwerp_naam", Value("-"), "wijk", output_field=models.CharField()
            )
        )
        meldingen = (
            meldingen.values("onderwerp_wijk", "onderwerp_naam", "wijk")
            .order_by("onderwerp_wijk")
            .annotate(count=Count("onderwerp_wijk"))
            .values("count", "onderwerp_naam", "wijk")
        )
        return meldingen

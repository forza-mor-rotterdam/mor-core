from apps.meldingen.models import Melding
from django.conf import settings
from django.db import connections
from django.db.models import Count, F, Value
from django.db.models.functions import Coalesce
from prometheus_client.core import CounterMetricFamily


class CustomCollector(object):
    def __init__(self):
        ...

    def collect(self):
        yield self.collect_taakopdracht_zonder_taak_url_metrics()
        yield self.collect_taakopdracht_zonder_taak_url_niet_actief_metrics()
        yield self.collect_melding_metrics()
        yield self.collect_taak_metrics()

    def collect_taakopdracht_zonder_taak_url_metrics(self):
        c = CounterMetricFamily(
            "morcore_taakopdracht_zonder_taak_url_total",
            "Taakopdracht aantallen zonder taak_url",
            labels=[
                "applicatie_naam",
                "applicatie_uuid",
            ],
        )
        total_taken = []

        sql = 'SELECT "applicaties_applicatie"."uuid", "applicaties_applicatie"."naam", \
            COUNT("taken_taakopdracht"."uuid") AS "count" \
            FROM "applicaties_applicatie" \
                JOIN "taken_taakopdracht" ON ("taken_taakopdracht"."applicatie_id" = "applicaties_applicatie"."id") \
                WHERE  \
                "taken_taakopdracht"."taak_url" IS NULL  \
                OR ("taken_taakopdracht"."taak_url" = \'\') IS TRUE  \
            GROUP BY "applicaties_applicatie"."uuid", 2 \
            ORDER BY "applicaties_applicatie"."uuid" ASC; \
        '

        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute(sql)
            total_taken = self.dictfetchall(cursor)

        for taak in total_taken:
            c.add_metric(
                (
                    taak["naam"],
                    str(taak["uuid"]),
                ),
                taak["count"],
            )

        return c

    def collect_taakopdracht_zonder_taak_url_niet_actief_metrics(self):
        c = CounterMetricFamily(
            "morcore_taakopdracht_zonder_taak_url_niet_actief_total",
            "Aantallen van taakopdrachten die niet gesynchroniseerd zijn met de taakapplicatie",
            labels=[
                "applicatie_naam",
            ],
        )
        total_taken = []

        sql = 'SELECT "applicaties_applicatie"."uuid", "applicaties_applicatie"."naam", \
            COUNT("taken_taakopdracht"."uuid") AS "count" \
            FROM "applicaties_applicatie" \
                JOIN "taken_taakopdracht" ON ("taken_taakopdracht"."applicatie_id" = "applicaties_applicatie"."id") \
                LEFT OUTER JOIN "django_celery_results_taskresult" ON ("taken_taakopdracht"."task_taak_aanmaken_id" = "django_celery_results_taskresult"."id") \
                WHERE  \
                ("taken_taakopdracht"."taak_url" IS NULL  \
                OR ("taken_taakopdracht"."taak_url" = \'\') IS TRUE)  \
                AND ("django_celery_results_taskresult"."status" = ANY(ARRAY[\'FAILED\', \'SUCCESS\'])  \
                OR "taken_taakopdracht"."task_taak_aanmaken_id" IS NULL)  \
            GROUP BY "applicaties_applicatie"."uuid", 2 \
            ORDER BY "applicaties_applicatie"."uuid" ASC; \
        '

        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute(sql)
            total_taken = self.dictfetchall(cursor)

        for taak in total_taken:
            c.add_metric(
                (taak["naam"],),
                taak["count"],
            )

        return c

    def collect_melding_metrics(self):
        c = CounterMetricFamily(
            "morcore_meldingen_total",
            "Melding aantallen",
            labels=[
                "onderwerp",
                "wijk",
                "status",
            ],
        )
        meldingen = (
            Melding.objects.filter(onderwerpen__response_json__name__isnull=False)
            .annotate(
                wijknaam=Coalesce(
                    F("referentie_locatie__wijknaam"),
                    Value("Onbekend"),
                )
            )
            .values("onderwerpen__response_json__name", "status__naam", "wijknaam")
            .annotate(count=Count("onderwerpen__response_json__name"))
            .values(
                "count", "onderwerpen__response_json__name", "status__naam", "wijknaam"
            )
        )

        for m in meldingen:
            c.add_metric(
                [
                    str(m.get("onderwerpen__response_json__name", "Onbekend")),
                    str(m.get("wijknaam", "Onbekend")),
                    str(m.get("status__naam")),
                ],
                m.get("count"),
            )
        return c

    def dictfetchall(self, cursor):
        """
        Return all rows from a cursor as a dict.
        Assume the column names are unique.
        """
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def collect_taak_metrics(self):
        c = CounterMetricFamily(
            "morcore_taken_total",
            "Taak aantallen",
            labels=[
                "taaktype",
                "status",
                "wijk",
            ],
        )
        total_taken = []
        sql = 'SELECT "taken_taakopdracht"."titel", "taken_taakstatus"."naam", COALESCE("locatie_locatie".wijknaam, \'Onbekend\') AS wijk, COUNT("taken_taakopdracht"."titel") AS "count" FROM "taken_taakopdracht" JOIN "taken_taakstatus" ON ("taken_taakopdracht"."status_id" = "taken_taakstatus"."id") JOIN "locatie_locatie" ON "locatie_locatie".melding_id = "taken_taakopdracht".melding_id JOIN "meldingen_melding" ON "meldingen_melding".referentie_locatie_id = "locatie_locatie".id GROUP BY "taken_taakopdracht"."titel", "taken_taakstatus"."naam", 3 ORDER BY "taken_taakopdracht"."titel" ASC;'

        with connections[settings.READONLY_DATABASE_KEY].cursor() as cursor:
            cursor.execute(sql)
            total_taken = self.dictfetchall(cursor)

        for taak in total_taken:
            c.add_metric(
                (
                    taak["titel"],
                    taak["naam"],
                    taak["wijk"],
                ),
                taak["count"],
            )

        return c

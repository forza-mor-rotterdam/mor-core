from datetime import datetime, timedelta

from apps.applicaties.models import Applicatie
from apps.locatie.models import Locatie
from apps.meldingen.models import Melding
from apps.services.pdok import PDOKService
from apps.signalen.models import Signaal
from apps.status.models import Status
from apps.taken.models import Taakopdracht
from django.conf import settings
from django.db import connections
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from prometheus_client.core import CounterMetricFamily
from shapely.wkt import loads


def duration_to_seconds(duration):
    """Converts a duration string to seconds."""
    return duration.total_seconds() if duration else None


class CustomCollector(object):
    def __init__(self):
        ...
        # self.taak_type_threshold_list = self.create_taaktype_threshold_list()
        self.annotated_wijken_taken = self.annotate_highest_weight_wijk(
            Taakopdracht.objects.all()
        )
        # self.annotated_threshold_taken = self.annotate_thresholds(
        #     self.annotated_wijken_taken
        # )

    def create_taaktype_threshold_list(self):
        taak_type_threshold_list = []
        taaktype_applicatie = Applicatie.vind_applicatie_obv_uri(
            settings.TAAKTYPE_APPLICATIE_URL
        )
        taaktype_data = taaktype_applicatie.taaktypes_halen(
            cache_timeout=900
        )  # Cache invalidates every 15 minutes
        for taaktype in taaktype_data:
            taak_type_threshold_list.append(
                {
                    "taaktype_url": taaktype["_links"].get("self", ""),
                    "threshold": taaktype.get("threshold", 3),
                    "titel": taaktype.get("omschrijving", ""),
                }
            )
        return taak_type_threshold_list

    def annotate_thresholds(self, queryset):
        return queryset.annotate(
            threshold=Case(
                *[
                    When(
                        taaktype=taaktype.get("taaktype_url", ""),
                        then=Value(taaktype.get("threshold", 3)),
                    )
                    for taaktype in self.taak_type_threshold_list
                ],
                default=Value(3),
            )
        )

    def annotate_highest_weight_wijk(self, queryset):
        locatie_subquery = (
            Locatie.objects.filter(melding=OuterRef("melding"))
            .order_by("-gewicht", "-aangemaakt_op")
            .distinct()
        )
        return queryset.annotate(
            highest_weight_wijk=Coalesce(
                Subquery(locatie_subquery.values("wijknaam")[:1]),
                Value("Onbekend"),
            ),
        )

    def collect(self):
        # Melding status metrics
        # yield self.collect_melding_status_duur_openstaand_metrics()

        # Meldingen metrics
        yield self.collect_melding_metrics()

        # # Signalen metrics
        # yield self.collect_signalen_metrics()

        # Taak total metrics
        yield self.collect_taak_metrics()

        # Taaktype threshold
        # yield self.collect_taaktype_threshold_metrics()

        # Taken langer dan taaktype threshold open
        # yield self.collect_taken_over_threshold_metrics()

        # Taken minder langer dan taaktype threshold open
        # yield self.collect_taken_onder_threshold_metrics()

        # Taak duur openstaand metrics
        # yield self.collect_taak_duur_metrics()

    def collect_signalen_metrics(self):
        c = CounterMetricFamily(
            "signalen",
            "Signalen aantalen gevarieerd op onderwerp en wijk",
            labels=[
                "onderwerp",
                "wijk",
                "lat",
                "lon",
            ],
        )

        wijken = PDOKService().get_wijken_middels_gemeentecode(
            gemeentecode=settings.WIJKEN_EN_BUURTEN_GEMEENTECODE
        )
        wijken_gps_lookup = {
            wijk.get("wijknaam"): wijk.get("centroide_ll") for wijk in wijken
        }
        signalen = (
            Signaal.objects.filter(onderwerpen__response_json__name__isnull=False)
            .annotate(
                wijknaam=Coalesce(
                    F("melding__referentie_locatie__wijknaam"),
                    Value("Onbekend"),
                )
            )
            .values("onderwerpen__response_json__name", "wijknaam")
            .annotate(count=Count("onderwerpen__response_json__name"))
            .values("count", "onderwerpen__response_json__name", "wijknaam")
        )
        for m in signalen:
            wijknaam = str(m.get("wijknaam", "Onbekend"))
            gps = (
                loads(wijken_gps_lookup.get(wijknaam))
                if wijken_gps_lookup.get(wijknaam)
                else ""
            )
            c.add_metric(
                [
                    str(m.get("onderwerpen__response_json__name", "Onbekend")),
                    wijknaam,
                    str(gps.coords[0][1]) if gps else "",
                    str(gps.coords[0][0]) if gps else "",
                ],
                m.get("count"),
            )
        return c

    def collect_melding_status_duur_openstaand_metrics(self):
        c = CounterMetricFamily(
            "melding_status_verandering_duur",
            "Toont de laatste status namen(status_eind) over het afgelopen uur. Met het voorlaatste status naam(status_begin) voor de bijbehoorde melding. De Count waarde is het verschil in seconden tussen status_eind en status_begin",
            labels=[
                "melding",
                "status_eind_aangemaakt_op",
                "status_eind",
                "status_begin",
                "onderwerp",
                "wijk",
            ],
        )
        now = datetime.now() - timedelta(hours=1)

        sub_all_statussen = Status.objects.filter(
            melding=OuterRef("melding"), aangemaakt_op__lt=OuterRef("aangemaakt_op")
        ).order_by("melding")

        sub = sub_all_statussen.values_list("melding", flat=True)

        sub_aangemaakt_op = sub_all_statussen.order_by("-aangemaakt_op").values_list(
            "aangemaakt_op", flat=True
        )[:1]
        sub_naam = sub_all_statussen.order_by("-aangemaakt_op").values_list(
            "naam", flat=True
        )[:1]
        sub_id = sub_all_statussen.order_by("-aangemaakt_op").values_list(
            "id", flat=True
        )[:1]
        sum_statussen_for_meldingen = sub.annotate(
            statussen_for_melding_sum=Count("melding")
        ).values("statussen_for_melding_sum")

        statussen = (
            Status.objects.annotate(
                onderwerpen_count=Count("melding__onderwerpen"),
                locaties_count=Count("melding__locaties_voor_melding"),
            )
            .exclude(
                onderwerpen_count=0,
                locaties_count=0,
            )
            .filter(
                aangemaakt_op__gte=now,
            )
            .annotate(status_count=Subquery(sum_statussen_for_meldingen))
            .filter(status_count__isnull=False)
            .order_by("-aangemaakt_op")
            .annotate(
                status_begin_naam=Subquery(sub_naam),
                status_begin_id=Subquery(sub_id),
                status_begin_aangemaakt_op=Subquery(sub_aangemaakt_op),
                duur=ExpressionWrapper(
                    F("aangemaakt_op") - Subquery(sub_aangemaakt_op),
                    output_field=DurationField(),
                ),
            )
        )
        for status in statussen:
            first_location = status.melding.locaties_voor_melding.order_by(
                "gewicht"
            ).first()
            c.add_metric(
                (
                    str(status.melding.id),
                    str(status.aangemaakt_op.timestamp()),
                    status.naam,
                    status.status_begin_naam,
                    str(
                        status.melding.onderwerpen.all()
                        .first()
                        .response_json.get("name")
                    ),
                    first_location.wijknaam if first_location.wijknaam else "",
                ),
                status.duur.seconds,
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

        # sql = 'SELECT "taken_taakopdracht"."titel", "taken_taakstatus"."naam", COALESCE("locatie_locatie".wijknaam, \'Onbekend\') AS wijk, COUNT("taken_taakopdracht"."titel") AS "count" FROM "taken_taakopdracht" JOIN "taken_taakstatus" ON ("taken_taakopdracht"."status_id" = "taken_taakstatus"."id") JOIN "locatie_locatie" ON "locatie_locatie".melding_id = "taken_taakopdracht".melding_id AND "locatie_locatie".primair = true GROUP BY "taken_taakopdracht"."titel", "taken_taakstatus"."naam", 3 ORDER BY "taken_taakopdracht"."titel" ASC;'
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

    def collect_taak_duur_metrics(self):
        c = CounterMetricFamily(
            "morcore_taken_duur_openstaand",
            "Taak duur openstaand",
            labels=["taaktype", "status", "wijk"],
        )
        taken = (
            self.annotated_wijken_taken.values(
                "titel",
                "status__naam",
                "highest_weight_wijk",
            )
            .order_by("titel")
            .annotate(
                avg_openstaand=Avg(
                    Case(
                        When(
                            afgesloten_op__isnull=False,
                            aangemaakt_op__isnull=False,
                            afhandeltijd__isnull=False,
                            then=F("afhandeltijd"),
                        ),
                        default=ExpressionWrapper(
                            timezone.now() - F("aangemaakt_op"),
                            output_field=DurationField(),
                        ),
                        output_field=DurationField(),
                    ),
                ),
            )
        )

        for taak in taken:
            if avg_openstaand_duration := taak.get("avg_openstaand"):
                avg_openstaand_seconds = avg_openstaand_duration.total_seconds()

                c.add_metric(
                    (
                        taak.get("titel"),
                        taak.get("status__naam"),
                        taak.get("highest_weight_wijk"),
                    ),
                    avg_openstaand_seconds,
                )
        return c

    def collect_taken_over_threshold_metrics(self):
        c = CounterMetricFamily(
            "morcore_taken_over_threshold",
            "Aantal taken langer open dan de threshold van het taaktype per wijk en taaktype",
            labels=["taaktype", "wijk"],
        )
        threshold_taken = (
            self.annotated_threshold_taken.filter(
                ~Q(status__naam__in=["voltooid", "voltooid_met_feedback"]),
                afgesloten_op__isnull=True,
                aangemaakt_op__lte=timezone.now()
                - timezone.timedelta(days=1) * F("threshold"),
            )
            .values("titel", "highest_weight_wijk")
            .order_by("titel")
            .annotate(count=Count("titel"))
        )

        for taak in threshold_taken:
            c.add_metric(
                (
                    taak.get("titel"),
                    taak.get("highest_weight_wijk"),
                ),
                taak.get("count"),
            )

        return c

    def collect_taken_onder_threshold_metrics(self):
        c = CounterMetricFamily(
            "morcore_taken_onder_threshold",
            "Aantal taken minder lang open dan de threshold van het taaktype per wijk en taaktype",
            labels=["taaktype", "wijk"],
        )

        taken = (
            self.annotated_threshold_taken.filter(
                ~Q(status__naam__in=["voltooid", "voltooid_met_feedback"]),
                afgesloten_op__isnull=True,
                aangemaakt_op__gt=timezone.now()
                - timezone.timedelta(days=1) * F("threshold"),
            )
            .values("titel", "highest_weight_wijk")
            .order_by("titel")
            .annotate(count=Count("titel"))
        )

        for taak in taken:
            c.add_metric(
                (
                    taak.get("titel"),
                    taak.get("highest_weight_wijk"),
                ),
                taak.get("count"),
            )

        return c

    def collect_taaktype_threshold_metrics(self):
        c = CounterMetricFamily(
            "morcore_taaktype_threshold",
            "De threshold in dagen van elk taaktype",
            labels=["taaktype", "taaktype_url"],
        )

        for taaktype in self.taak_type_threshold_list:
            taaktype_url = taaktype.get("taaktype_url", "")
            threshold = taaktype.get("threshold", 3)
            titel = taaktype.get("titel", "")

            c.add_metric((titel, taaktype_url), threshold)

        return c

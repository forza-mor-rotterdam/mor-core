import logging

from dateutil import parser
from django.contrib.gis.db import models
from django.db.models import (
    Avg,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Min,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.expressions import Func
from django.db.models.functions import Coalesce, Concat

logger = logging.getLogger(__name__)


class Epoch(Func):
    template = "EXTRACT(epoch FROM %(expressions)s)::DOUBLE PRECISION"
    output_field = models.FloatField()


class StatusQuerySet(QuerySet):
    def veranderingen(self, params):
        from apps.aliassen.models import OnderwerpAlias
        from apps.locatie.models import Locatie
        from apps.status.models import Status

        statussen = self.all()

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
        sum_statussen_for_meldingen = sub.annotate(
            statussen_for_melding_sum=Count("melding")
        ).values("statussen_for_melding_sum")

        # annotate with onderwerp & wijk
        locaties = Locatie.objects.filter(melding=OuterRef("melding")).order_by(
            "-gewicht"
        )
        onderwerpen = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("melding")
        )
        statussen = statussen.annotate(
            onderwerp=Coalesce(
                Subquery(onderwerpen.values("response_json__name")[:1]),
                Value("Onbekend", output_field=models.JSONField()),
            )
        ).annotate(
            wijk=Coalesce(
                Subquery(locaties.values("wijknaam")[:1]),
                Value("Onbekend"),
            )
        )

        # filter out statussen whithout previous status, meaning there is no duration between only one status.
        statussen = statussen.annotate(
            status_count=Subquery(sum_statussen_for_meldingen)
        ).filter(status_count__isnull=False)

        # add previous status naam
        statussen = statussen.annotate(
            begin_status=Subquery(sub_naam), eind_status=F("naam")
        )

        # add unique combined value for averages later
        statussen = statussen.annotate(
            eind_begin_wijk_onderwerp=Concat(
                "naam",
                Value("-"),
                "eind_status",
                Value("-"),
                "onderwerp",
                Value("-"),
                "wijk",
                output_field=models.CharField(),
            )
        ).order_by("eind_begin_wijk_onderwerp")

        # add duration between begin and end status
        statussen = statussen.annotate(
            duur_seconden=ExpressionWrapper(
                Epoch(F("aangemaakt_op")) - Epoch(Subquery(sub_aangemaakt_op)),
                output_field=FloatField(),
            )
        )

        # add average duration between begin and end status
        statussen = statussen.values(
            "eind_begin_wijk_onderwerp",
            "wijk",
            "onderwerp",
            "begin_status",
            "eind_status",
        ).annotate(
            duur_seconden_gemiddeld=Avg(
                F("duur_seconden"),
                output_field=FloatField(),
            ),
            aantal=Count(F("eind_begin_wijk_onderwerp")),
        )

        return statussen.values(
            "wijk",
            "onderwerp",
            "begin_status",
            "eind_status",
            "duur_seconden_gemiddeld",
            "aantal",
        )

    def doorlooptijden_afgehandelde_meldingen(self, params):
        from apps.aliassen.models import OnderwerpAlias
        from apps.locatie.models import Locatie
        from apps.status.models import Status

        locaties = Locatie.objects.filter(melding=OuterRef("melding")).order_by(
            "-gewicht"
        )
        onderwerpen = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("melding")
        )

        aangemaakt_op_gte = None
        aangemaakt_op_lt = None
        try:
            aangemaakt_op_gte = parser.parse(params.get("aangemaakt_op_gte"))
            aangemaakt_op_lt = parser.parse(params.get("aangemaakt_op_lt"))
        except Exception:
            ...

        qs = Status.objects.all()

        if aangemaakt_op_lt:
            qs = qs.filter(
                aangemaakt_op__lt=aangemaakt_op_lt,
            )

        # annotate met duur van status
        qs = qs.annotate(
            duur=Coalesce(
                ExpressionWrapper(
                    Epoch(
                        Subquery(
                            Status.objects.filter(
                                melding=OuterRef("melding"),
                                aangemaakt_op__gt=OuterRef("aangemaakt_op"),
                            )
                            .order_by()
                            .annotate(min=Min("aangemaakt_op"))
                            .values("min")[:1]
                        )
                    )
                    - Epoch(F("aangemaakt_op")),
                    output_field=FloatField(),
                ),
                0,
                output_field=FloatField(),
            ),
        )

        # subquery aantallen per status naam optie
        qs_aantal = (
            Status.objects.filter(melding=OuterRef("melding")).values("naam").order_by()
        )
        # subquery voor totale duur van de status instanties per naam optie
        qs_duur = qs.filter(melding=OuterRef("melding")).values("naam").order_by()

        for status_naam, _ in Status.NaamOpties.choices:
            annotations = [
                {
                    f"{status_naam}_aantal": Subquery(
                        qs_aantal.filter(
                            naam=status_naam,
                        )
                        .annotate(val=Count("naam"))
                        .values("val")[:1]
                    ),
                },
                {
                    f"{status_naam}_duur_totaal": Subquery(
                        qs_duur.filter(
                            naam=status_naam,
                        )
                        .annotate(val=Sum("duur"))
                        .values("val")[:1]
                    ),
                },
            ]
            for annotation in annotations:
                qs = qs.annotate(**annotation)

        # filter op laatste afgehandelde status instanties
        qs = qs.filter(
            duur=0,
            naam__in=[Status.NaamOpties.AFGEHANDELD, Status.NaamOpties.GEANNULEERD],
        )
        if aangemaakt_op_gte:
            qs = qs.filter(
                aangemaakt_op__gte=aangemaakt_op_gte,
            )

        # annotate met wijk en onderwerp
        qs = qs.annotate(
            onderwerp=Coalesce(
                Subquery(onderwerpen.values("response_json__name")[:1]),
                Value("Onbekend", output_field=models.JSONField()),
            )
        ).annotate(
            wijk=Coalesce(
                Subquery(locaties.values("wijknaam")[:1]),
                Value("Onbekend"),
            )
        )
        # annotate met onderwerp & wijk gecombineerde voor ontdubbeling
        qs = qs.annotate(
            onderwerp_wijk=Concat(
                "onderwerp", Value("-"), "wijk", output_field=models.CharField()
            )
        )

        # annotate met gemiddelden van totaal aantal en totaal duur van statussen
        avg_fields = [
            {
                f"{naam}_aantal_gemiddeld": Avg(
                    F(f"{naam}_aantal"),
                    output_field=FloatField(),
                ),
                f"{naam}_duur_gemiddeld": Avg(
                    F(f"{naam}_duur_totaal"),
                    output_field=FloatField(),
                    filter=~Q(**{f"{naam}_duur_totaal": 0}),
                ),
            }
            for naam, _ in Status.NaamOpties.choices
        ]
        avg_fields.insert(0, {"melding_aantal": Count("onderwerp_wijk")})
        avg_fields = {k: v for a in avg_fields for k, v in a.items()}

        end_values = list(
            ["melding_aantal", "wijk", "onderwerp"]
            + [
                n
                for naam, _ in Status.NaamOpties.choices
                for n in [f"{naam}_aantal_gemiddeld", f"{naam}_duur_gemiddeld"]
            ]
        )

        qs = (
            qs.values("onderwerp_wijk", "wijk", "onderwerp")
            .order_by()
            .annotate(**avg_fields)
            .values(*end_values)
        )
        return qs

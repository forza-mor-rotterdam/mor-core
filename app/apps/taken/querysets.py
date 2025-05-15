import logging

from django.contrib.gis.db import models
from django.db.models import (
    Avg,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Min,
    OuterRef,
    QuerySet,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce, Concat
from utils.models import Epoch

logger = logging.getLogger(__name__)


class TaakopdrachtQuerySet(QuerySet):
    def taaktype_aantallen_per_melding(self, querystring):
        from apps.aliassen.models import OnderwerpAlias

        inclusief_melding = querystring.get("inclusief-melding", False)

        onderwerpen = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("melding")
        )
        taakopdrachten = self.all()

        taakopdrachten = taakopdrachten.annotate(
            onderwerp=Coalesce(
                Subquery(onderwerpen.values("response_json__name")[:1]),
                Value("Onbekend", output_field=models.JSONField()),
            )
        ).annotate(
            wijk=Coalesce(
                F("melding__referentie_locatie__wijknaam"),
                Value("Onbekend"),
            )
        )

        taakopdrachten = (
            taakopdrachten.annotate(
                melding_taaktype=Concat(
                    "melding", Value("-"), "taaktype", output_field=models.CharField()
                )
            )
            .values("melding_taaktype", "titel", "wijk", "onderwerp")
            .order_by()
        )
        taakopdrachten = taakopdrachten.annotate(
            taaktype_melding_aantal=Count("melding_taaktype")
        )

        taakopdrachten = (
            taakopdrachten.annotate(
                onderwerp_wijk_taaktype_aantal=Concat(
                    "onderwerp",
                    Value("-"),
                    "wijk",
                    Value("-"),
                    "taaktype",
                    Value("-"),
                    "taaktype_melding_aantal",
                    output_field=models.CharField(),
                )
            )
            .values(
                "onderwerp_wijk_taaktype_aantal",
                "taaktype",
                "wijk",
                "onderwerp",
                "taaktype_melding_aantal",
                "melding",
                "melding__uuid",
                "titel",
            )
            .order_by()
        )

        taakopdrachten = list(
            {
                taakopdracht.get("onderwerp_wijk_taaktype_aantal"): {
                    "wijk": taakopdracht.get("wijk"),
                    "onderwerp": taakopdracht.get("onderwerp"),
                    "taaktype": taakopdracht.get("taaktype"),
                    "titel": taakopdracht.get("titel"),
                    "aantal_per_melding": taakopdracht.get("taaktype_melding_aantal"),
                    "melding_aantal": len(
                        [
                            to
                            for to in taakopdrachten
                            if to.get("onderwerp_wijk_taaktype_aantal")
                            == taakopdracht.get("onderwerp_wijk_taaktype_aantal")
                        ]
                    ),
                    "meldingen": [
                        to.get("melding__uuid")
                        for to in taakopdrachten
                        if to.get("onderwerp_wijk_taaktype_aantal")
                        == taakopdracht.get("onderwerp_wijk_taaktype_aantal")
                    ]
                    if inclusief_melding
                    else [],
                }
                for taakopdracht in taakopdrachten
            }.values()
        )
        return taakopdrachten

    def taakopdracht_doorlooptijden(self):
        from apps.aliassen.models import OnderwerpAlias
        from apps.taken.models import Taakgebeurtenis

        onderwerpen = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("melding")
        )
        taakopdrachten = self.all()

        # als het maar wel afgesloten Taakgebeurtenis instancies zijn
        taakopdrachten = taakopdrachten.filter(afgesloten_op__isnull=False)

        # annotate Taakgebeurtenis sub met eerste en laatste Taakgebeurtenis
        sub_taakgebeurtenis_min = (
            Taakgebeurtenis.objects.filter(
                taakopdracht=OuterRef("pk"),
            )
            .order_by("-aangemaakt_op")
            .annotate(
                min=Min("aangemaakt_op"),
            )
            .values("min")
        )

        sub_taakgebeurtenis_max = (
            Taakgebeurtenis.objects.filter(
                taakopdracht=OuterRef("pk"),
            )
            .order_by("aangemaakt_op")
            .annotate(
                max=Min("aangemaakt_op"),
            )
            .values("max")
        )

        # annotate met tijds verschil tussen eerste en laatste Taakgebeurtenis
        taakopdrachten = taakopdrachten.annotate(
            duur=Coalesce(
                ExpressionWrapper(
                    Epoch(Subquery(sub_taakgebeurtenis_min.values("min")[:1]))
                    - Epoch(Subquery(sub_taakgebeurtenis_max.values("max")[:1])),
                    output_field=FloatField(),
                ),
                0,
                output_field=FloatField(),
            ),
        )

        # annotate met onderwerp en wijk
        taakopdrachten = taakopdrachten.annotate(
            onderwerp=Coalesce(
                Subquery(onderwerpen.values("response_json__name")[:1]),
                Value("Onbekend", output_field=models.JSONField()),
            )
        ).annotate(
            wijk=Coalesce(
                F("melding__referentie_locatie__wijknaam"),
                Value("Onbekend"),
            )
        )

        taakopdrachten = taakopdrachten.values(
            "taaktype", "titel", "titel", "wijk", "onderwerp", "duur"
        ).order_by()

        taakopdrachten = (
            (
                taakopdrachten.annotate(
                    onderwerp_wijk_taaktype=Concat(
                        "onderwerp",
                        Value("-"),
                        "wijk",
                        Value("-"),
                        "taaktype",
                        output_field=models.CharField(),
                    )
                )
            )
            .values("onderwerp_wijk_taaktype", "taaktype", "titel", "wijk", "onderwerp")
            .order_by()
        )
        taakopdrachten = taakopdrachten.annotate(
            taakopdracht_aantal=Count("onderwerp_wijk_taaktype"),
            duur_gemiddeld=Avg("duur"),
        )

        taakopdrachten = taakopdrachten.values(
            "taaktype",
            "titel",
            "wijk",
            "onderwerp",
            "taakopdracht_aantal",
            "duur_gemiddeld",
        )
        return taakopdrachten

    def nieuwe_taakopdrachten(self):
        from apps.aliassen.models import OnderwerpAlias

        taakopdrachten = self
        onderwerpen = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("melding")
        )

        # annotate met onderwerp en wijk
        taakopdrachten = taakopdrachten.annotate(
            onderwerp=Coalesce(
                Subquery(onderwerpen.values("response_json__name")[:1]),
                Value("Onbekend", output_field=models.JSONField()),
            )
        ).annotate(
            wijk=Coalesce(
                F("melding__referentie_locatie__wijknaam"),
                Value("Onbekend"),
            )
        )

        taakopdrachten = taakopdrachten.values(
            "taaktype", "titel", "titel", "wijk", "onderwerp"
        ).order_by()

        taakopdrachten = (
            (
                taakopdrachten.annotate(
                    onderwerp_wijk_taaktype=Concat(
                        "onderwerp",
                        Value("-"),
                        "wijk",
                        Value("-"),
                        "taaktype",
                        output_field=models.CharField(),
                    )
                )
            )
            .values("onderwerp_wijk_taaktype", "taaktype", "titel", "wijk", "onderwerp")
            .order_by()
        )

        taakopdrachten = taakopdrachten.annotate(
            taakopdracht_aantal=Count("onderwerp_wijk_taaktype"),
        )

        taakopdrachten = taakopdrachten.values(
            "taaktype",
            "titel",
            "wijk",
            "onderwerp",
            "taakopdracht_aantal",
        )
        return taakopdrachten

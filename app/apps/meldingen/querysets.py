import logging

from django.contrib.gis.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat

logger = logging.getLogger(__name__)


class MeldingQuerySet(QuerySet):
    def get_aantallen(self):
        from apps.aliassen.models import OnderwerpAlias
        from apps.locatie.models import Locatie

        meldingen = self.prefetch_related("onderwerpen", "locatis_voor_melding")
        locaties_subquery = Locatie.objects.filter(melding=OuterRef("pk")).order_by(
            "-gewicht"
        )[:1]
        onderwerpen_subquery = OnderwerpAlias.objects.filter(
            meldingen_voor_onderwerpen=OuterRef("pk")
        ).values("response_json__name")[:1]

        meldingen = (
            meldingen.annotate(
                onderwerp=Coalesce(
                    Subquery(onderwerpen_subquery),
                    Value("Onbekend", output_field=models.JSONField()),
                )
            )
            .annotate(
                wijk=Coalesce(
                    Subquery(locaties_subquery.values("wijknaam")),
                    Value("Onbekend"),
                )
            )
            .annotate(
                onderwerp_wijk=Concat(
                    "onderwerp", Value("-"), "wijk", output_field=models.CharField()
                )
            )
            .order_by("onderwerp_wijk")
            .values("onderwerp_wijk", "onderwerp", "wijk")
        )

        meldingen = meldingen.annotate(count=Count("id")).values(
            "count", "onderwerp", "wijk"
        )

        return meldingen

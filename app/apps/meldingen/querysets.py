import logging

from django.contrib.gis.db import models
from django.db.models import Count, F, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce, Concat

logger = logging.getLogger(__name__)


class MeldingQuerySet(QuerySet):
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

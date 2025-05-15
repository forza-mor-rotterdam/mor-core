import logging

from django.contrib.gis.db import models
from django.db.models import Count, F, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce, Concat

logger = logging.getLogger(__name__)


class SignaalQuerySet(QuerySet):
    def get_aantallen(self):
        from apps.aliassen.models import OnderwerpAlias

        onderwerpen = OnderwerpAlias.objects.filter(
            signalen_voor_onderwerpen=OuterRef("pk")
        )
        signalen = self.all()

        signalen = signalen.annotate(
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
        signalen = signalen.annotate(
            onderwerp_wijk=Concat(
                "onderwerp", Value("-"), "wijk", output_field=models.CharField()
            )
        )
        signalen = (
            signalen.values("onderwerp_wijk", "onderwerp", "wijk")
            .order_by("onderwerp_wijk")
            .annotate(count=Count("onderwerp_wijk"))
            .values("count", "onderwerp", "wijk")
        )
        [m.get("count") for m in signalen]
        return signalen

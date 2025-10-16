import requests
import urllib3
from django.contrib.gis.db import models
from utils.fields import DictJSONField
from utils.models import BasisModel


class OnderwerpAlias(BasisModel):
    bron_url = models.CharField(max_length=500)
    response_json = DictJSONField(
        default=dict,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Onderwerp alias"
        verbose_name_plural = "Onderwerp aliassen"

    class OnderwerpNietValide(Exception):
        pass

    def _valideer_bron_url(self, bron_url: str):
        response = requests.get(
            bron_url,
            headers={
                "user-agent": urllib3.util.SKIP_HEADER,
            },
        )
        if response.status_code != 200:
            raise OnderwerpAlias.OnderwerpNietValide
        return response.json()

    def save(self, *args, **kwargs):
        self.response_json = self._valideer_bron_url(self.bron_url)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        try:
            return self.response_json.get("name", self.bron_url)
        except Exception:
            return self.bron_url

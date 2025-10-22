from django.contrib.gis.db import models
from utils.models import BasisModel


class Instelling(BasisModel):
    onderwerpen_basis_url = models.URLField(default="http://onderwerpen.mor.local:8006")

    @classmethod
    def actieve_instelling(cls):
        instellingen = cls.objects.all()
        if not instellingen:
            raise Exception("Er zijn nog instellingen aangemaakt")
        return instellingen[0]

    def valideer_url(self, veld, url):
        if veld not in ("onderwerpen_basis_url",):
            return False
        return url.startswith(getattr(self, veld))

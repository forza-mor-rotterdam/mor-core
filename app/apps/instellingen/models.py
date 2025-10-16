from django.contrib.gis.db import models
from utils.models import BasisModel


class Instelling(BasisModel):
    onderwerpen_basis_url = models.URLField(default="http://onderwerpen.mor.local:8006")

    @classmethod
    def actieve_instelling(cls):
        eerst_gevonden_instelling = cls.objects.first()
        if not eerst_gevonden_instelling:
            raise Exception("Er zijn nog instellingen aangemaakt")
        return eerst_gevonden_instelling

    def valideer_url(self, veld, url):
        if veld not in ("onderwerpen_basis_url",):
            return False
        return url.startswith(getattr(self, veld))

from django.contrib.gis.db import models
from utils.models import BasisModel


class Melder(BasisModel):
    naam = models.CharField(max_length=100, blank=True, null=True)
    voornaam = models.CharField(max_length=50, blank=True, null=True)
    achternaam = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefoonnummer = models.CharField(max_length=17, blank=True, null=True)

    class Meta:
        verbose_name = "Melder"
        verbose_name_plural = "Melders"

    def get_zoek_tekst(self):
        return {
            "voornaam_achternaam": f"{self.voornaam or ''} {self.achternaam or ''}".strip(),
            "email": f"{self.email or ''}".strip(),
            "naam": f"{self.naam or ''}".strip(),
            "telefoonnummer": f"{self.telefoonnummer or ''}".strip(),
        }

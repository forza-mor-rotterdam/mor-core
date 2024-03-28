from apps.applicaties.models import Applicatie
from apps.bijlagen.models import Bijlage
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db import models
from utils.fields import DictJSONField
from utils.models import BasisModel


class Signaal(BasisModel):
    """
    Een signaal een individuele signaal vanuit de buiten ruimte.
    Er kunnen meerdere signalen aan een melding gekoppeld zijn, bijvoorbeeld dubbele signalen.
    Maar er altijd minimaal een signaal gerelateerd aan een Melding.
    Er mag binnen deze applicatie geen extra info over een signaal

    Het verwijzing veld, moet nog nader bepaald worden. Vermoedelijk wordt dit een url
    """

    signaal_url = models.URLField()
    signaal_data = models.JSONField(default=dict)
    bron_id = models.CharField(max_length=500, null=True, blank=True)
    bron_signaal_id = models.CharField(max_length=500, null=True, blank=True)
    origineel_aangemaakt = models.DateTimeField(null=True, blank=True)
    urgentie = models.FloatField(default=0.2)
    omschrijving_melder = models.CharField(max_length=500, null=True, blank=True)
    aanvullende_informatie = models.CharField(max_length=5000, null=True, blank=True)
    aanvullende_vragen = models.JSONField(default=list)
    meta = DictJSONField(default=dict)
    meta_uitgebreid = DictJSONField(default=dict)
    melder = models.OneToOneField(
        to="melders.Melder", on_delete=models.SET_NULL, null=True, blank=True
    )
    melding = models.ForeignKey(
        to="meldingen.Melding",
        related_name="signalen_voor_melding",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    bijlagen = GenericRelation(Bijlage)
    onderwerpen = models.ManyToManyField(
        to="aliassen.OnderwerpAlias",
        related_name="signalen_voor_onderwerpen",
        blank=True,
    )

    @property
    def get_graven(self):
        return self.locaties_voor_signaal

    @property
    def get_lichtmasten(self):
        return self.locaties_voor_signaal

    @property
    def get_adressen(self):
        return self.locaties_voor_signaal

    def notificatie_melding_afgesloten(self):
        applicatie = Applicatie.vind_applicatie_obv_uri(self.signaal_url)
        applicatie.notificatie_melding_afgesloten(self.signaal_url)

    class Meta:
        verbose_name = "Signaal"
        verbose_name_plural = "Signalen"
        unique_together = (
            "bron_id",
            "bron_signaal_id",
        )

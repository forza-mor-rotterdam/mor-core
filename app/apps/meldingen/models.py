import logging

from apps.bijlagen.models import Bijlage
from apps.meldingen.managers import MeldingManager
from apps.meldingen.querysets import MeldingQuerySet
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db import models
from django.contrib.sites.models import Site
from rest_framework.reverse import reverse
from utils.fields import DictJSONField
from utils.models import BasisModel

logger = logging.getLogger(__name__)


class Meldinggebeurtenis(BasisModel):
    """
    MeldingGebeurtenissen bouwen de history op van van de melding
    """

    class GebeurtenisType(models.TextChoices):
        STANDAARD = "standaard", "Standaard"
        STATUS_WIJZIGING = "status_wijziging", "Status wijziging"
        MELDING_AANGEMAAKT = "melding_aangemaakt", "Melding aangemaakt"
        TAAKOPDRACHT_AANGEMAAKT = "taakopdracht_aangemaakt", "Taakopdracht aangemaakt"
        TAAKOPDRACHT_VERWIJDERD = "taakopdracht_verwijderd", "Taakopdracht verwijderd"
        TAAKOPDRACHT_NOTIFICATIE = (
            "taakopdracht_notificatie",
            "Taakopdracht notificatie",
        )
        TAAKOPDRACHT_STATUS_WIJZIGING = (
            "taakopdracht_status_wijziging",
            "Taakopdracht status wijziging",
        )
        LOCATIE_AANGEMAAKT = "locatie_aangemaakt", "Locatie aangemaakt"
        SIGNAAL_TOEGEVOEGD = "signaal_toegevoegd", "Signaal toegevoegd"
        URGENTIE_AANGEPAST = "urgentie_aangepast", "Urgentie aangepast"
        MELDING_HEROPEND = "melding_heropend", "Melding heropend"

    gebeurtenis_type = models.CharField(
        max_length=40,
        choices=GebeurtenisType.choices,
        default=GebeurtenisType.STANDAARD,
    )
    urgentie = models.FloatField(null=True, blank=True)
    bijlagen = GenericRelation(Bijlage)
    status = models.OneToOneField(
        to="status.Status",
        related_name="meldinggebeurtenis_voor_status",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    omschrijving_intern = models.CharField(max_length=5000, null=True, blank=True)
    omschrijving_extern = models.CharField(max_length=2000, null=True, blank=True)
    gebruiker = models.CharField(max_length=200, null=True, blank=True)
    melding = models.ForeignKey(
        to="meldingen.Melding",
        related_name="meldinggebeurtenissen_voor_melding",
        on_delete=models.CASCADE,
    )
    taakopdracht = models.ForeignKey(
        to="taken.Taakopdracht",
        related_name="meldinggebeurtenissen_voor_taakopdracht",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    taakgebeurtenis = models.ForeignKey(
        to="taken.Taakgebeurtenis",
        related_name="meldinggebeurtenissen_voor_taakgebeurtenis",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    locatie = models.ForeignKey(
        to="locatie.Locatie",
        related_name="meldinggebeurtenissen_voor_locatie",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    signaal = models.ForeignKey(
        to="signalen.Signaal",
        related_name="meldinggebeurtenissen_voor_signaal",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-aangemaakt_op",)
        verbose_name = "Melding gebeurtenis"
        verbose_name_plural = "Melding gebeurtenissen"


class Melding(BasisModel):
    """
    Een melding is de ontdubbelde versie van signalen
    """

    """
    Als er geen taak_applicaties zijn linked aan deze melding, kan b.v. MidOffice deze handmatig toewijzen
    """

    class ResolutieOpties(models.TextChoices):
        OPGELOST = "opgelost", "Opgelost"
        NIET_OPGELOST = "niet_opgelost", "Niet opgelost"

    origineel_aangemaakt = models.DateTimeField()
    afgesloten_op = models.DateTimeField(null=True, blank=True)
    urgentie = models.FloatField(default=0.2)
    meta = DictJSONField(default=dict)
    meta_uitgebreid = DictJSONField(default=dict)
    status = models.OneToOneField(
        to="status.Status",
        related_name="melding_voor_status",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    resolutie = models.CharField(
        max_length=50,
        choices=ResolutieOpties.choices,
        default=ResolutieOpties.NIET_OPGELOST,
    )
    bijlagen = GenericRelation(Bijlage)
    onderwerpen = models.ManyToManyField(
        to="aliassen.OnderwerpAlias",
        related_name="meldingen_voor_onderwerpen",
        blank=True,
    )

    objects = MeldingQuerySet.as_manager()
    acties = MeldingManager()

    @property
    def get_graven(self):
        return self.locaties_voor_melding

    @property
    def get_lichtmasten(self):
        return self.locaties_voor_melding

    @property
    def get_adressen(self):
        return self.locaties_voor_melding

    @property
    def actieve_taakopdrachten(self):
        from apps.taken.models import Taakstatus

        return self.taakopdrachten_voor_melding.exclude(
            status__naam__in=[
                Taakstatus.NaamOpties.VOLTOOID,
                Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
            ],
            verwijderd_op__isnull=False,
        )

    def get_absolute_url(self):
        domain = Site.objects.get_current().domain
        url_basis = f"{settings.PROTOCOL}://{domain}{settings.PORT}"
        pad = reverse(
            "v1:melding-detail",
            kwargs={"uuid": self.uuid},
        )
        return f"{url_basis}{pad}"

    class Meta:
        verbose_name = "Melding"
        verbose_name_plural = "Meldingen"

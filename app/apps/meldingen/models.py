import logging
import uuid

from apps.bijlagen.models import Bijlage
from apps.meldingen.managers import MeldingManager
from apps.meldingen.querysets import MeldingQuerySet
from apps.signalen.models import Signaal
from apps.taken.models import Taakgebeurtenis
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.sites.models import Site
from django.db.models import Q
from django_extensions.db.fields import AutoSlugField
from rest_framework.reverse import reverse
from utils.fields import DictJSONField
from utils.models import BasisModel

logger = logging.getLogger(__name__)


class ResolutieOpties(models.TextChoices):
    OPGELOST = "opgelost", "Opgelost"
    NIET_OPGELOST = "niet_opgelost", "Niet opgelost"


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
    resolutie = models.CharField(
        max_length=50,
        choices=ResolutieOpties.choices,
        blank=True,
        null=True,
    )
    afhandelreden = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    specificatie = models.ForeignKey(
        to="meldingen.Specificatie",
        related_name="meldinggebeurtenissen_voor_specificatie",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
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

    origineel_aangemaakt = models.DateTimeField()
    afgesloten_op = models.DateTimeField(null=True, blank=True)
    afhandelreden = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    specificatie = models.ForeignKey(
        to="meldingen.Specificatie",
        related_name="meldingen_voor_specificatie",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
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
        blank=True,
        null=True,
    )
    bijlagen = GenericRelation(Bijlage)
    thumbnail_afbeelding = models.OneToOneField(
        to="bijlagen.Bijlage",
        related_name="melding_voor_bijlage",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    onderwerpen = models.ManyToManyField(
        to="aliassen.OnderwerpAlias",
        related_name="meldingen_voor_onderwerpen",
        blank=True,
    )
    onderwerp = models.URLField(
        blank=True,
        null=True,
    )
    referentie_locatie = models.OneToOneField(
        to="locatie.Locatie",
        related_name="melding_voor_locatie",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    zoek_tekst = models.TextField(
        default="",
        blank=True,
        null=True,
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

    def get_zoek_tekst(self):
        from apps.locatie.models import Locatie
        from apps.melders.models import Melder

        signalen_voor_melding = self.signalen_voor_melding.all()
        melders = Melder.objects.filter(
            id__in=list(signalen_voor_melding.values_list("melder__id", flat=True))
        )
        locaties_voor_melding = (
            Locatie.objects.exclude(locatie_type="lichtmast")
            .filter(
                Q(melding__id=self.id)
                | Q(
                    signaal__id__in=list(
                        signalen_voor_melding.values_list("id", flat=True)
                    )
                )
            )
            .distinct()
        )

        locatie_zoek_teksten = [
            locatie.get_zoek_tekst() for locatie in locaties_voor_melding
        ]

        bron_signaal_ids = list(
            signalen_voor_melding.filter(
                bron_signaal_id__isnull=False,
            ).values_list("bron_signaal_id", flat=True)
        )

        melder_zoek_dicts = [melder.get_zoek_tekst() for melder in melders]
        melder_zoek_teksten = [
            melder_dict[melder_zoek_field]
            for melder_dict in melder_zoek_dicts
            for melder_zoek_field in [
                "voornaam_achternaam",
                "email",
                "naam",
                "telefoonnummer",
            ]
        ]

        return ",".join(
            list(
                set(
                    [
                        tekst
                        for tekst in bron_signaal_ids
                        + locatie_zoek_teksten
                        + melder_zoek_teksten
                        if tekst
                    ]
                )
            )
        )

    def get_bijlagen(self, order_by="aangemaakt_op"):
        bijlagen = Bijlage.objects.filter(
            (
                Q(object_id=self.id)
                & Q(content_type=ContentType.objects.get_for_model(Melding))
            )
            | (
                Q(object_id__in=self.signalen_voor_melding.values_list("id", flat=True))
                & Q(content_type=ContentType.objects.get_for_model(Signaal))
            )
            | (
                Q(
                    object_id__in=self.meldinggebeurtenissen_voor_melding.values_list(
                        "id", flat=True
                    )
                )
                & Q(content_type=ContentType.objects.get_for_model(Meldinggebeurtenis))
            )
            | (
                Q(
                    object_id__in=[
                        taakgebeurtenis.id
                        for taakopdracht in self.taakopdrachten_voor_melding.all()
                        for taakgebeurtenis in taakopdracht.taakgebeurtenissen_voor_taakopdracht.all()
                    ]
                )
                & Q(content_type=ContentType.objects.get_for_model(Taakgebeurtenis))
            )
        ).order_by(order_by)
        return bijlagen

    @property
    def actieve_taakopdrachten(self):
        from apps.taken.models import Taakstatus

        taakopdrachten_voor_melding = self.taakopdrachten_voor_melding.all()

        taakopdrachten_voor_melding_zonder_valide_taken = (
            taakopdrachten_voor_melding.exclude(
                Q(
                    status__naam__in=[
                        Taakstatus.NaamOpties.VOLTOOID,
                        Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
                    ]
                )
                | Q(verwijderd_op__isnull=False),
            )
        )
        return taakopdrachten_voor_melding_zonder_valide_taken

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


class Specificatie(BasisModel):
    uuid = models.UUIDField(
        auto_created=True,
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="id",
    )
    naam = models.CharField(
        max_length=255,
        unique=True,
    )
    slug = AutoSlugField(
        populate_from=("naam",),
        overwrite=True,
        editable=True,
        unique=True,
    )
    verwijderd_op = models.DateTimeField(
        null=True,
        blank=True,
    )

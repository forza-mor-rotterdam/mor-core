from apps.bijlagen.models import Bijlage
from apps.taken.querysets import TaakopdrachtQuerySet
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db import models
from django.contrib.sites.models import Site
from django.db.models import Q
from django_celery_results.models import TaskResult
from rest_framework.exceptions import APIException
from rest_framework.reverse import reverse
from utils.django_celery_results import restart_task
from utils.fields import DictJSONField
from utils.models import BasisModel


class Taakgebeurtenis(BasisModel):
    """
    Taakgebeurtenissen bouwen de history op van een taak
    """

    class ResolutieOpties(models.TextChoices):
        OPGELOST = "opgelost", "Opgelost"
        NIET_OPGELOST = "niet_opgelost", "Niet opgelost"
        GEANNULEERD = "geannuleerd", "Geannuleerd"
        NIET_GEVONDEN = "niet_gevonden", "Niets aangetroffen"

    verwijderd_op = models.DateTimeField(null=True, blank=True)
    afgesloten_op = models.DateTimeField(null=True, blank=True)
    bijlagen = GenericRelation(Bijlage)
    taakstatus = models.ForeignKey(
        to="taken.Taakstatus",
        related_name="taakgebeurtenissen_voor_taakstatus",
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
    omschrijving_intern = models.CharField(max_length=5000, null=True, blank=True)
    gebruiker = models.CharField(max_length=200, null=True, blank=True)
    taakopdracht = models.ForeignKey(
        to="taken.Taakopdracht",
        related_name="taakgebeurtenissen_voor_taakopdracht",
        on_delete=models.CASCADE,
    )
    additionele_informatie = DictJSONField(default=dict)

    class Meta:
        ordering = ("-aangemaakt_op",)
        verbose_name = "Taakgebeurtenis"
        verbose_name_plural = "Taakgebeurtenissen"


class Taakstatus(BasisModel):
    class NaamOpties(models.TextChoices):
        NIEUW = "nieuw", "Nieuw"
        VOLTOOID = "voltooid", "Voltooid"
        VOLTOOID_MET_FEEDBACK = "voltooid_met_feedback", "Voltooid met feedback"

    naam = models.CharField(
        max_length=50,
        default=NaamOpties.NIEUW,
    )
    taakopdracht = models.ForeignKey(
        to="taken.Taakopdracht",
        related_name="taakstatussen_voor_taakopdracht",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-aangemaakt_op",)

    def __str__(self) -> str:
        return f"{self.naam}({self.pk})"

    def clean(self):
        huidige_status = (
            self.taakopdracht.status.naam if self.taakopdracht.status else ""
        )
        nieuwe_status = self.naam
        if huidige_status == nieuwe_status:
            raise Taakstatus.TaakStatusVeranderingNietToegestaan(
                "De nieuwe taakstatus mag niet hezelfde zijn als de huidige"
            )

    class TaakStatusVeranderingNietToegestaan(APIException):
        pass

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Taakopdracht(BasisModel):
    """
    Taakapplicaties kunnen een taakopdracht aanmaken in more-core.
    Op basis van de taakopdracht wordt er een taak aangemaakt in een applicatie.
    In de response zit de taak_url, die weer opgeslagen wordt in deze taakopdracht.
    Zo worden taakopdrachten aan taken gelinked.
    """

    class ResolutieOpties(models.TextChoices):
        OPGELOST = "opgelost", "Opgelost"
        NIET_OPGELOST = "niet_opgelost", "Niet opgelost"
        GEANNULEERD = "geannuleerd", "Geannuleerd"
        NIET_GEVONDEN = "niet_gevonden", "Niets aangetroffen"

    afgesloten_op = models.DateTimeField(null=True, blank=True)
    afhandeltijd = models.DurationField(null=True, blank=True)
    verwijderd_op = models.DateTimeField(null=True, blank=True)
    melding = models.ForeignKey(
        to="meldingen.Melding",
        related_name="taakopdrachten_voor_melding",
        on_delete=models.CASCADE,
    )
    # This is the taakapplicatie (FixeR/ExternR)
    applicatie = models.ForeignKey(
        to="applicaties.Applicatie",
        related_name="taakopdrachten_voor_applicatie",
        on_delete=models.CASCADE,
    )
    # We may want to include the taaktypeapplicatie (TaakR)
    taaktype = models.CharField(
        max_length=200,
    )
    titel = models.CharField(
        max_length=200,
    )
    bericht = models.CharField(
        max_length=5000,
        blank=True,
        null=True,
    )
    status = models.ForeignKey(
        to="taken.Taakstatus",
        related_name="taakopdrachten_voor_taakstatus",
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
    additionele_informatie = DictJSONField(default=dict)

    taak_url = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )
    task_taak_aanmaken = models.OneToOneField(
        to="django_celery_results.TaskResult",
        related_name="taakopdracht",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    taak_aanmaken_error = models.CharField(max_length=5000, null=True, blank=True)

    objects = TaakopdrachtQuerySet.as_manager()

    class AanmakenNietToegestaan(APIException):
        ...

    class Meta:
        ordering = ("-aangemaakt_op",)
        verbose_name = "Taakopdracht"
        verbose_name_plural = "Taakopdrachten"
        indexes = [
            models.Index(fields=["uuid"], name="taakopdracht_uuid_idx"),
        ]

    @property
    def is_voltooid(self):
        return (
            self.status
            and self.status.naam
            in [
                Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
                Taakstatus.NaamOpties.VOLTOOID,
            ]
            or self.verwijderd_op
        )

    def get_task_taak_aanmaken(self):
        from apps.taken.tasks import task_taak_aanmaken_v2

        task_taak_aanmaken_taskresult = task_taak_aanmaken_v2.delay(
            taakopdracht_uuid=str(self.uuid),
        )
        taskresults = TaskResult.objects.filter(
            task_id=task_taak_aanmaken_taskresult.task_id
        )
        return taskresults[0] if taskresults else None

    def start_task_taak_aanmaken(self):
        if not self.task_taak_aanmaken:
            self.task_taak_aanmaken = self.get_task_taak_aanmaken()
            self.save(update_fields=["task_taak_aanmaken"])
        else:
            aangemaakt, message = restart_task(self.task_taak_aanmaken)
            if not aangemaakt:
                raise Exception(
                    f"Het is niet gelukt om de bestaande tasks te herstarten: {message}"
                )

    def valideer_en_set_resolutie(self, nieuwe_resolutie):
        self.resolutie = Taakopdracht.ResolutieOpties.OPGELOST
        if nieuwe_resolutie in [ro[0] for ro in Taakopdracht.ResolutieOpties.choices]:
            self.resolutie = nieuwe_resolutie

    def clean(self):
        if self.pk is None:
            openstaande_taken = self.melding.taakopdrachten_voor_melding.exclude(
                Q(
                    status__naam__in=[
                        Taakstatus.NaamOpties.VOLTOOID,
                        Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
                    ]
                )
                | Q(verwijderd_op__isnull=False)
            )
            gebruikte_taaktypes = list(
                {
                    taaktype
                    for taaktype in openstaande_taken.values_list("taaktype", flat=True)
                    .order_by("taaktype")
                    .distinct()
                }
            )
            if self.taaktype in gebruikte_taaktypes:
                raise Taakopdracht.AanmakenNietToegestaan(
                    "Er is al een taakopdracht met dit taaktype voor deze melding"
                )

    def save(self, *args, **kwargs):
        if self.afgesloten_op and self.aangemaakt_op:
            self.afhandeltijd = self.afgesloten_op - self.aangemaakt_op
        else:
            self.afhandeltijd = None
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        domain = Site.objects.get_current().domain
        url_basis = f"{settings.PROTOCOL}://{domain}{settings.PORT}"
        pad = reverse(
            "v1:taakopdracht-detail",
            kwargs={"uuid": self.uuid},
        )
        return f"{url_basis}{pad}"

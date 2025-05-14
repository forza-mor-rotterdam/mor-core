from apps.locatie.querysets import AdresQuerySet, GrafQuerySet, LichtmastQuerySet
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from utils.models import BasisModel


class GenericRelationMixin(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True


class GeometrieBasis(BasisModel, GenericRelationMixin):
    """
    Klasse voor het opslaan van geografische informatie.
    """

    geometrie = models.GeometryField()

    class Meta:
        abstract = True


class Geometrie(GeometrieBasis):
    """
    Klasse voor het opslaan van geografische informatie.
    """


LOCATIE_TYPE_CHOICES = (
    ("adres", "adres"),
    ("lichtmast", "lichtmast"),
    ("graf", "graf"),
)


class Locatie(BasisModel):
    melding = models.ForeignKey(
        to="meldingen.Melding",
        related_name="locaties_voor_melding",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    signaal = models.ForeignKey(
        to="signalen.Signaal",
        related_name="locaties_voor_signaal",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    locatie_type = models.CharField(
        max_length=50, choices=LOCATIE_TYPE_CHOICES, default=LOCATIE_TYPE_CHOICES[0][0]
    )
    locatie_zoek_field = models.CharField(max_length=512, null=True, blank=True)
    geometrie = models.GeometryField(null=True, blank=True)
    bron = models.CharField(max_length=50, null=True, blank=True)
    naam = models.CharField(max_length=255, null=True, blank=True)
    plaatsnaam = models.CharField(max_length=255, null=True, blank=True)
    straatnaam = models.CharField(max_length=255, null=True, blank=True)
    huisnummer = models.IntegerField(null=True, blank=True)
    huisletter = models.CharField(max_length=1, null=True, blank=True)
    toevoeging = models.CharField(max_length=4, null=True, blank=True)
    postcode = models.CharField(max_length=7, null=True, blank=True)
    wijknaam = models.CharField(max_length=255, null=True, blank=True)
    buurtnaam = models.CharField(max_length=255, null=True, blank=True)
    lichtmast_id = models.CharField(max_length=255, null=True, blank=True)
    plaatsnaam = models.CharField(max_length=255, null=True, blank=True)
    begraafplaats = models.CharField(max_length=50, null=True, blank=True)
    grafnummer = models.CharField(max_length=10, null=True, blank=True)
    vak = models.CharField(max_length=10, null=True, blank=True)
    gebruiker = models.ForeignKey(
        to="authenticatie.Gebruiker",
        related_name="locatie_voor_gebruiker",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    gewicht = models.FloatField(default=0.2)
    primair = models.BooleanField(default=False)

    def get_zoek_tekst(self):
        if self.locatie_type == "adres":
            return f"{self.straatnaam or ''} {self.huisnummer or ''}{self.huisletter or ''}{'-' + self.toevoeging if self.toevoeging else ''}".strip()
        elif self.locatie_type == "graf":
            return f"{self.grafnummer or ''} {self.vak or ''}".strip()
        return ""

    def bereken_gewicht(self):
        return self.gewicht

    @property
    def custom_gewicht_property(self):
        return self.bereken_gewicht()

    class Meta:
        indexes = [
            models.Index(
                fields=["buurtnaam", "wijknaam"], name="buurtnaam_wijknaam_idx"
            ),
            models.Index(fields=["buurtnaam"], name="buurtnaam_idx"),
            models.Index(fields=["wijknaam"], name="wijknaam_idx"),
        ]


class Adres(Locatie):
    """
    Basis klasse voor adres informatie.
    """

    objects = AdresQuerySet()

    def save(self, *args, **kwargs):
        self.locatie_type = "adres"
        super().save(*args, **kwargs)

    class Meta:
        proxy = True


class Lichtmast(Locatie):
    """
    Basis klasse voor lichtmast informatie.
    """

    objects = LichtmastQuerySet()

    def save(self, *args, **kwargs):
        self.locatie_type = "lichtmast"
        super().save(*args, **kwargs)

    class Meta:
        proxy = True


class Graf(Locatie):
    """
    Klasse voor het opslaan van graf locatie informatie.
    """

    objects = GrafQuerySet()

    def save(self, *args, **kwargs):
        self.locatie_type = "graf"
        super().save(*args, **kwargs)

    class Meta:
        proxy = True

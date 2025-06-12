from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import Melding, ResolutieOpties


class StatusFilter(admin.SimpleListFilter):
    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        status_namen = Melding.objects.values_list("status__naam", flat=True).distinct()
        return ((status_naam, status_naam) for status_naam in set(status_namen))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status__naam=self.value())
        return queryset


class ResolutieFilter(admin.SimpleListFilter):
    title = _("Resolutie")
    parameter_name = "resolutie"

    def lookups(self, request, model_admin):
        return ResolutieOpties.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(resolutie=self.value())
        else:
            return queryset


class AfgeslotenOpFilter(admin.SimpleListFilter):
    title = _("Afgesloten")
    parameter_name = "afgesloten"

    def lookups(self, request, model_admin):
        return (
            ("ja", _("Ja")),
            ("nee", _("Nee")),
        )

    def queryset(self, request, queryset):
        if self.value() == "ja":
            return queryset.exclude(afgesloten_op__isnull=True)
        elif self.value() == "nee":
            return queryset.filter(afgesloten_op__isnull=True)
        else:
            return queryset


class BijlagenAantalFilter(admin.SimpleListFilter):
    title = "Bijlagen aantal"
    parameter_name = "bijlagen_aantal"

    def lookups(self, request, model_admin):
        return (("bijlagen_aantal__gt", "1 of meer"),)

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.annotate(bijlagen_aantal=Count("bijlagen")).filter(
                **{self.value(): 0}
            )
        return queryset


class ThumbnailAfbeeldingFilter(admin.SimpleListFilter):
    title = "Thumbnail afbeelding"
    parameter_name = "thumbnail_afbeelding"

    def lookups(self, request, model_admin):
        return (("thumbnail_afbeelding__isnull", "Geen thumbnail"),)

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.filter(**{self.value(): True})
        return queryset


class ReferentieLocatieFilter(admin.SimpleListFilter):
    title = "Referentie locatie"
    parameter_name = "referentie_locatie"

    def lookups(self, request, model_admin):
        return (("referentie_locatie__isnull", "Geen referentie locatie"),)

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.filter(**{self.value(): True})
        return queryset


class ZoekTekstFilter(admin.SimpleListFilter):
    title = "Zoek tekst"
    parameter_name = "zoek_tekst"

    def lookups(self, request, model_admin):
        return (
            ("zoek_tekst_niet_gezet", "Zoek tekst is None"),
            ("zoek_tekst_lege_string", "Zoek tekst is ''"),
        )

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == "zoek_tekst_niet_gezet":
                return queryset.filter(zoek_tekst__isnull=True)
            if self.value() == "zoek_tekst_lege_string":
                return queryset.filter(zoek_tekst="")
        return queryset


class OnderwerpenFilter(admin.SimpleListFilter):
    title = _("Onderwerp")
    parameter_name = "onderwerp"

    def lookups(self, request, model_admin):
        onderwerpen = [
            str(onderwerp)
            for onderwerp in Melding.objects.values_list(
                "onderwerpen__response_json__name", flat=True
            ).distinct()
            if onderwerp
        ]
        return ((onderwerp, onderwerp) for onderwerp in sorted(set(onderwerpen)))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(onderwerpen__response_json__name=self.value())
        else:
            return queryset

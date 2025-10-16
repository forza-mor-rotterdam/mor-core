from apps.taken.models import Taakopdracht
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class TaakUrlFilter(admin.SimpleListFilter):
    title = _("Taak url")
    parameter_name = "taak_url"

    def lookups(self, request, model_admin):
        return (
            ("true", "taak url aanwezig"),
            ("false", "taak url niet aanwezig"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                taakopdracht__taak_url__isnull=(self.value() == "false"),
            )
        return queryset


class SyncedFilter(admin.SimpleListFilter):
    title = _("Synced met FixeR")
    parameter_name = "synced"

    def lookups(self, request, model_admin):
        return (
            ("true", "synced"),
            ("false", "niet gesynced"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                additionele_informatie__taak_url__isnull=(self.value() == "false"),
            )
        return queryset


class TaakStatusFilter(admin.SimpleListFilter):
    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        status_namen = Taakopdracht.objects.values_list(
            "status__naam", flat=True
        ).distinct()
        return ((status_naam, status_naam) for status_naam in set(status_namen))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(taakstatus__naam=self.value())
        return queryset


class StatusFilter(admin.SimpleListFilter):
    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        status_namen = Taakopdracht.objects.values_list(
            "status__naam", flat=True
        ).distinct()
        return ((status_naam, status_naam) for status_naam in set(status_namen))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status__naam=self.value())
        return queryset


class ResolutieFilter(admin.SimpleListFilter):
    title = _("Resolutie")
    parameter_name = "resolutie"

    def lookups(self, request, model_admin):
        return Taakopdracht.ResolutieOpties.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(resolutie=self.value())
        else:
            return queryset


class TitelFilter(admin.SimpleListFilter):
    title = _("Titel")
    parameter_name = "titel"

    def lookups(self, request, model_admin):
        titels = Taakopdracht.objects.values_list("titel", flat=True).distinct()
        return ((titel, titel) for titel in sorted(set(titels)))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(titel=self.value())
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

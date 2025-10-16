import logging

from apps.meldingen.admin_filters import (
    AfgeslotenOpFilter,
    BijlagenAantalFilter,
    OnderwerpenFilter,
    ReferentieLocatieFilter,
    ResolutieFilter,
    StatusFilter,
    ThumbnailAfbeeldingFilter,
    ZoekTekstFilter,
)
from apps.meldingen.models import Melding, Meldinggebeurtenis, Specificatie
from apps.meldingen.tasks import (
    task_bijlages_voor_geselecteerde_meldingen_opruimen,
    task_notificatie_voor_signaal_melding_afgesloten,
    task_set_melding_thumbnail_afbeelding_voor_melding_reeks,
    task_vernieuw_melding_zoek_tekst_voor_melding_reeks,
)
from apps.status.models import Status
from django.conf import settings
from django.contrib import admin

logger = logging.getLogger(__name__)


@admin.action(description="Melding met alle relaties verwijderen")
def action_melding_met_alle_relaties_verwijderen(modeladmin, request, queryset):
    for melding in queryset.all():
        Melding.acties.melding_verwijderen(melding)


@admin.action(description="Signalen afsluiten voor melding")
def action_notificatie_voor_signaal_melding_afgesloten(modeladmin, request, queryset):
    for melding in queryset.all():
        if (
            melding.afgesloten_op
            and melding.status.naam != Status.NaamOpties.GEANNULEERD
        ):
            for signaal in melding.signalen_voor_melding.all():
                task_notificatie_voor_signaal_melding_afgesloten.delay(signaal.uuid)


@admin.action(description="Melding bijlages opruimen")
def action_melding_bijlages_opruimen(modeladmin, request, queryset):
    logger.info(f"settings.ENVIRONMENT: {settings.ENVIRONMENT}")
    task_bijlages_voor_geselecteerde_meldingen_opruimen.delay(
        list(queryset.filter(afgesloten_op__isnull=False).values_list("id", flat=True))
    )


@admin.action(description="Set melding.thumbnail_afbeelding voor meldingen")
def action_set_melding_thumbnail_afbeelding_voor_melding_reeks(
    modeladmin, request, queryset
):
    task_set_melding_thumbnail_afbeelding_voor_melding_reeks.delay(
        melding_ids=list(queryset.values_list("id", flat=True))
    )


@admin.action(description="Vernieuw melding.zoek_tekst voor meldingen")
def action_vernieuw_melding_zoek_tekst_voor_melding_reeks(
    modeladmin, request, queryset
):
    task_vernieuw_melding_zoek_tekst_voor_melding_reeks.delay(
        melding_ids=list(queryset.values_list("id", flat=True))
    )


class SpecificatieAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "naam",
        "aantal_meldingen",
    )
    search_fields = [
        "uuid",
        "meldingen_voor_specificatie__uuid",
    ]

    def aantal_meldingen(self, obj):
        return obj.meldingen_voor_specificatie.count()

    aantal_meldingen.short_description = "Aantal meldingen"


class MeldingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bijlage_aantal",
        "thumbnail_afbeelding",
        "uuid",
        "urgentie",
        "resolutie",
        "afhandelreden",
        "specificatie",
        "afgesloten_op",
        "status_naam",
        "onderwerp_naam",
        "referentie_locatie",
        "origineel_aangemaakt",
        "aangemaakt_op",
        "aangepast_op",
        "zoek_tekst",
    )
    list_filter = (
        "specificatie",
        "afhandelreden",
        ThumbnailAfbeeldingFilter,
        ReferentieLocatieFilter,
        ZoekTekstFilter,
        BijlagenAantalFilter,
        StatusFilter,
        ResolutieFilter,
        AfgeslotenOpFilter,
        OnderwerpenFilter,
    )
    search_fields = [
        "id",
        "uuid",
    ]
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
        "afgesloten_op",
        "origineel_aangemaakt",
    )
    raw_id_fields = (
        "status",
        "referentie_locatie",
        "thumbnail_afbeelding",
        "specificatie",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "uuid",
                    "urgentie",
                    "status",
                    "resolutie",
                    "afhandelreden",
                    "specificatie",
                    "onderwerpen",
                    "referentie_locatie",
                )
            },
        ),
        (
            "Tijden",
            {
                "fields": (
                    "aangemaakt_op",
                    "origineel_aangemaakt",
                    "aangepast_op",
                    "afgesloten_op",
                )
            },
        ),
        (
            "Meta info",
            {
                "fields": (
                    "meta",
                    "meta_uitgebreid",
                )
            },
        ),
    )

    actions = (
        action_notificatie_voor_signaal_melding_afgesloten,
        action_melding_met_alle_relaties_verwijderen,
        action_melding_bijlages_opruimen,
        action_set_melding_thumbnail_afbeelding_voor_melding_reeks,
        action_vernieuw_melding_zoek_tekst_voor_melding_reeks,
    )

    def bijlage_aantal(self, obj):
        try:
            return obj.bijlagen.count()
        except Exception:
            return "0"

    def status_naam(self, obj):
        try:
            return obj.status.naam
        except Exception:
            return "- leeg -"

    def onderwerp_naam(self, obj):
        try:
            return ", ".join(
                [
                    onderwerp.response_json.get("name")
                    for onderwerp in obj.onderwerpen.all()
                ]
            )
        except Exception:
            return "- leeg -"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "status",
        ).prefetch_related(
            "thumbnail_afbeelding",
            "onderwerpen",
            "referentie_locatie",
            "bijlagen",
        )


class MeldinggebeurtenisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "gebeurtenis_type",
        "aangemaakt_op",
        "melding",
        "omschrijving_extern",
        "omschrijving_intern",
        "taakopdracht",
        "taakgebeurtenis",
        "signaal",
        "gebruiker",
    )
    raw_id_fields = (
        "status",
        "specificatie",
        "melding",
        "taakopdracht",
        "taakgebeurtenis",
        "signaal",
        "locatie",
    )
    search_fields = (
        "uuid",
        "status__uuid",
        "specificatie__uuid",
        "signaal__uuid",
        "locatie__uuid",
        "melding__uuid",
        "taakopdracht__uuid",
        "taakgebeurtenis__uuid",
    )
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "status",
            "locatie",
            "signaal",
            "specificatie",
            "melding",
            "taakopdracht",
            "taakgebeurtenis",
        )


admin.site.register(Meldinggebeurtenis, MeldinggebeurtenisAdmin)
admin.site.register(Melding, MeldingAdmin)
admin.site.register(Specificatie, SpecificatieAdmin)

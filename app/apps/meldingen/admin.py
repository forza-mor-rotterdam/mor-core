from apps.meldingen.admin_filters import (
    AfgeslotenOpFilter,
    OnderwerpenFilter,
    ResolutieFilter,
    StatusFilter,
)
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.meldingen.tasks import (
    task_bijlages_voor_geselecteerde_meldingen_opruimen,
    task_notificatie_voor_signaal_melding_afgesloten,
)
from apps.status.models import Status
from django.contrib import admin


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
                task_notificatie_voor_signaal_melding_afgesloten.delay(signaal.id)


@admin.action(description="Melding bijlages opruimen")
def action_melding_bijlages_opruimen(modeladmin, request, queryset):
    task_bijlages_voor_geselecteerde_meldingen_opruimen.delay(
        list(queryset.filter(afgesloten_op__isnull=False).values_list("id", flat=True))
    )


class MeldingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "urgentie",
        "status_naam",
        "onderwerp_naam",
        "locatie",
        "origineel_aangemaakt",
        "aangemaakt_op",
        "aangepast_op",
        "afgesloten_op",
    )
    list_filter = (
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
    raw_id_fields = ("status",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "uuid",
                    "urgentie",
                    "status",
                    "resolutie",
                    "onderwerpen",
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
    )

    def status_naam(self, obj):
        try:
            return obj.status.naam
        except Exception:
            return "- leeg -"

    def onderwerp_naam(self, obj):
        try:
            return ", ".join(
                list(obj.onderwerpen.values_list("response_json__name", flat=True))
            )
        except Exception:
            return "- leeg -"

    def locatie(self, obj):
        try:
            return ", ".join(
                list(
                    obj.locaties_voor_melding.order_by("-gewicht").values_list(
                        "wijknaam", flat=True
                    )
                )
            )
        except Exception:
            return "- leeg -"


class MeldinggebeurtenisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "gebeurtenis_type",
        "aangemaakt_op",
        "melding",
        "omschrijving_extern",
        "taakopdracht",
        "taakgebeurtenis",
        "signaal",
    )
    raw_id_fields = (
        "melding",
        "taakopdracht",
        "taakgebeurtenis",
        "signaal",
        "locatie",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "signaal",
            "melding",
            "taakopdracht",
            "taakgebeurtenis",
        )


admin.site.register(Meldinggebeurtenis, MeldinggebeurtenisAdmin)
admin.site.register(Melding, MeldingAdmin)

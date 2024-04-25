from apps.meldingen.admin_filters import (
    AfgeslotenOpFilter,
    OnderwerpenFilter,
    ResolutieFilter,
    StatusFilter,
)
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.meldingen.tasks import task_notificatie_voor_signaal_melding_afgesloten
from apps.status.models import Status
from django.contrib import admin


@admin.action(description="Signalen afsluiten voor melding")
def action_notificatie_voor_signaal_melding_afgesloten(modeladmin, request, queryset):
    for melding in queryset.all():
        if (
            melding.afgesloten_op
            and melding.status.naam != Status.NaamOpties.GEANNULEERD
        ):
            for signaal in melding.signalen_voor_melding.all():
                task_notificatie_voor_signaal_melding_afgesloten.delay(signaal.id)


class MeldingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "urgentie",
        "status_naam",
        "onderwerp_naam",
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
    ]
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
        "afgesloten_op",
        "origineel_aangemaakt",
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

    actions = (action_notificatie_voor_signaal_melding_afgesloten,)

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


admin.site.register(Meldinggebeurtenis, MeldinggebeurtenisAdmin)
admin.site.register(Melding, MeldingAdmin)

from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.meldingen.tasks import (
    convert_aanvullende_informatie_to_aanvullende_vragen,
    task_notificatie_voor_signaal_melding_afgesloten,
)
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

    # Define the custom admin action
    def convert_to_aanvullende_vragen(self, request, queryset):
        melding_ids = queryset.values_list("id", flat=True)
        convert_aanvullende_informatie_to_aanvullende_vragen(melding_ids)
        self.message_user(request, "Conversion started for selected meldingen.")

    convert_to_aanvullende_vragen.short_description = (
        "Convert aanvullende informatie to aanvullende vragen"
    )

    # Register the admin action
    actions = (
        action_notificatie_voor_signaal_melding_afgesloten,
        convert_to_aanvullende_vragen,
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


class MeldinggebeurtenisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "aangemaakt_op",
        "melding",
        "omschrijving_extern",
    )


admin.site.register(Meldinggebeurtenis, MeldinggebeurtenisAdmin)
admin.site.register(Melding, MeldingAdmin)

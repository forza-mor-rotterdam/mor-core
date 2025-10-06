from apps.signalen.admin_filters import BijlagenAantalFilter
from apps.signalen.models import Signaal
from django.contrib import admin

from .tasks import convert_aanvullende_informatie_to_aanvullende_vragen


class SignaalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "signaal_url",
        "bijlage_aantal",
        "aangemaakt_op",
        "aangepast_op",
        "bron_id",
        "bron_signaal_id",
        "melding",
        "melder",
    )

    # Define the custom admin action
    def convert_to_aanvullende_vragen(self, request, queryset):
        signaal_ids = list(queryset.values_list("id", flat=True))
        convert_aanvullende_informatie_to_aanvullende_vragen.delay(signaal_ids)
        self.message_user(request, "Conversion started for selected signaals.")

    convert_to_aanvullende_vragen.short_description = (
        "Convert aanvullende informatie to aanvullende vragen"
    )

    list_filter = (
        BijlagenAantalFilter,
        "bron_id",
    )

    # Register the admin action
    actions = [convert_to_aanvullende_vragen]
    search_fields = [
        "bron_signaal_id",
        "uuid",
        "melding__uuid",
    ]
    raw_id_fields = (
        "melding",
        "melder",
    )

    def bijlage_aantal(self, obj):
        try:
            return obj.bijlagen.count()
        except Exception:
            return "0"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "melding",
            "melder",
        ).prefetch_related("bijlagen")


admin.site.register(Signaal, SignaalAdmin)

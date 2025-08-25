from apps.melders.models import Melder
from django.contrib import admin


class DefaultAdmin(admin.ModelAdmin):
    list_display = ("id", "uuid", "naam", "signaal")
    search_fields = (
        "uuid",
        "signaal__uuid",
        "signaal__melding__uuid",
    )
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "signaal",
        )


admin.site.register(Melder, DefaultAdmin)

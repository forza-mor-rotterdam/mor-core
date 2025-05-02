from apps.bijlagen.tasks import task_aanmaken_afbeelding_versies, task_bijlage_opruimen
from apps.meldingen.models import Bijlage
from django.contrib import admin


@admin.action(description="Maak afbeelding versies voor selectie")
def action_aanmaken_afbeelding_versies(modeladmin, request, queryset):
    for bijlage in queryset.all():
        task_aanmaken_afbeelding_versies.delay(bijlage.id)


@admin.action(description="Bijlage opruimen")
def action_bijlage_opruimen(modeladmin, request, queryset):
    for bijlage in queryset.all():
        task_bijlage_opruimen.delay(bijlage.id)


class BijlageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "bestand_hash",
        "aangemaakt_op",
        "is_afbeelding",
        "mimetype",
        "content_type",
        "object_id",
        "bestand",
        "afbeelding",
        "afbeelding_verkleind",
        "opgeruimd_op",
    )
    list_filter = ("content_type",)
    actions = (
        action_aanmaken_afbeelding_versies,
        action_bijlage_opruimen,
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "content_object",
        )


admin.site.register(Bijlage, BijlageAdmin)

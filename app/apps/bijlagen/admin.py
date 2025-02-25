from apps.bijlagen.tasks import (
    task_aanmaken_afbeelding_versies,
    task_minify_origineel_bijlage_bestand,
)
from apps.meldingen.models import Bijlage
from django.contrib import admin


@admin.action(description="Maak afbeelding versies voor selectie")
def action_aanmaken_afbeelding_versies(modeladmin, request, queryset):
    for bijlage in queryset.all():
        task_aanmaken_afbeelding_versies.delay(bijlage.id)


@admin.action(description="Minify origeel bestand voor selectie")
def action_minify_origineel_bijlage_bestanden(modeladmin, request, queryset):
    for bijlage in queryset.all():
        task_minify_origineel_bijlage_bestand.delay(bijlage.id)


class BijlageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "aangemaakt_op",
        "bestand",
        "is_afbeelding",
        "mimetype",
        "content_object",
        "afbeelding",
    )
    actions = (
        action_aanmaken_afbeelding_versies,
        action_minify_origineel_bijlage_bestanden,
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "content_object",
        )


admin.site.register(Bijlage, BijlageAdmin)

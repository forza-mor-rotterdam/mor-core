from apps.locatie.models import Adres, Graf, Lichtmast, Locatie
from apps.locatie.tasks import update_locatie_zoek_field_task
from django.contrib import admin, messages
from django.contrib.gis import forms
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.forms.widgets import Textarea


class AdresForm(forms.ModelForm):
    latitude = forms.FloatField(
        min_value=-90,
        max_value=90,
        required=True,
    )
    longitude = forms.FloatField(
        min_value=-180,
        max_value=180,
        required=True,
    )

    class Meta(object):
        model = Adres
        exclude = []
        widgets = {"geometrie": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        coordinates = self.initial.get("geometrie", None)
        if isinstance(coordinates, Point):
            self.initial["longitude"], self.initial["latitude"] = coordinates.tuple

    def clean(self):
        data = super().clean()
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        data.get("geometrie")
        if latitude and longitude:
            data["geometrie"] = Point(longitude, latitude)
        return data


class GrafAdmin(admin.ModelAdmin):
    list_display = ("id", "uuid", "aangemaakt_op", "begraafplaats")


class LocatieAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "aangemaakt_op",
        "begraafplaats",
        "melding",
        "wijknaam",
        "gewicht",
        "primair",
        "signaal",
        "huisnummer",
        "straatnaam",
        "geometrie",
    )
    search_fields = [
        "id",
        "melding__uuid",
    ]
    list_filter = ("primair",)

    # TODO: Remove later!!!
    formfield_overrides = {
        models.GeometryField: {"widget": Textarea(attrs={"rows": 2})}
    }
    raw_id_fields = (
        "melding",
        "signaal",
        "gebruiker",
    )
    actions = ["update_locatie_zoek_field"]

    @admin.action(description="Update locatie_zoek_field for selected locations")
    def update_locatie_zoek_field(self, request, queryset):
        locatie_ids = list(queryset.values_list("id", flat=True))
        task = update_locatie_zoek_field_task.delay(locatie_ids)
        self.message_user(
            request,
            f"Task to update locatie_zoek_field for {len(locatie_ids)} locations has been queued. Task ID: {task.id}",
            messages.SUCCESS,
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "melding",
            "signaal",
        )


class AdresAdmin(admin.ModelAdmin):
    list_display = ("id", "uuid", "aangemaakt_op", "melding", "signaal", "straatnaam")
    form = AdresForm


class LichtmastAdmin(admin.ModelAdmin):
    list_display = ("id", "uuid", "aangemaakt_op", "melding", "signaal", "lichtmast_id")


admin.site.register(Graf, GrafAdmin)
admin.site.register(Adres, AdresAdmin)
admin.site.register(Lichtmast, LichtmastAdmin)
admin.site.register(Locatie, LocatieAdmin)

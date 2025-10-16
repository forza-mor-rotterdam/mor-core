import urllib.parse
from urllib.parse import urlparse

from apps.aliassen.models import OnderwerpAlias
from apps.instellingen.models import Instelling
from apps.meldingen.models import Melding
from apps.signalen.models import Signaal
from django.contrib import admin


@admin.action(description="Link meldingen aan valide onderwerp")
def action_link_meldingen_aan_valide_onderwerp(modeladmin, request, queryset):
    instelling = Instelling.actieve_instelling()
    for onderwerp in queryset.all():
        if not instelling.valideer_url("onderwerpen_basis_url", onderwerp.bron_url):
            melding_ids = Melding.objects.filter(onderwerpen=onderwerp).values_list(
                "id", flat=True
            )
            signal_ids = Signaal.objects.filter(onderwerpen=onderwerp).values_list(
                "id", flat=True
            )

            url_obj = urlparse(onderwerp.bron_url)
            bron_url = urllib.parse.urljoin(
                instelling.onderwerpen_basis_url, url_obj.path
            )
            valide_onderwerp, _ = OnderwerpAlias.objects.get_or_create(
                bron_url=bron_url
            )

            onderwerp.meldingen_voor_onderwerpen.remove(*melding_ids)
            onderwerp.signalen_voor_onderwerpen.remove(*signal_ids)

            valide_onderwerp.meldingen_voor_onderwerpen.add(*melding_ids)
            valide_onderwerp.signalen_voor_onderwerpen.add(*signal_ids)


class OnderwerpAliasAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bron_url",
        "naam",
        "aangemaakt_op",
        "aantal_meldingen",
        "aantal_signalen",
    )

    search_fields = (
        "uuid",
        "meldingen_voor_onderwerpen__uuid",
        "signalen_voor_onderwerpen__uuid",
    )
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
    )

    actions = (action_link_meldingen_aan_valide_onderwerp,)

    def naam(self, obj):
        return obj.response_json.get("name", "")

    def aantal_meldingen(self, obj):
        return obj.meldingen_voor_onderwerpen.count()

    def aantal_signalen(self, obj):
        return obj.signalen_voor_onderwerpen.count()

    naam.short_description = "Naam"
    aantal_meldingen.short_description = "Aantal meldingen"
    aantal_signalen.short_description = "Aantal signalen"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "signalen_voor_onderwerpen",
            "meldingen_voor_onderwerpen",
        )


admin.site.register(OnderwerpAlias, OnderwerpAliasAdmin)

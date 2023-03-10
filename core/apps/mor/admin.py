from apps.mor.models import (
    Bijlage,
    Geometrie,
    Melding,
    MeldingGebeurtenis,
    MeldingGebeurtenisType,
    Signaal,
    TaakApplicatie,
)
from django.contrib import admin


class DefaultAdmin(admin.ModelAdmin):
    pass


admin.site.register(TaakApplicatie, DefaultAdmin)
admin.site.register(MeldingGebeurtenisType, DefaultAdmin)
admin.site.register(MeldingGebeurtenis, DefaultAdmin)
admin.site.register(Melding, DefaultAdmin)
admin.site.register(Geometrie, DefaultAdmin)
admin.site.register(Signaal, DefaultAdmin)
admin.site.register(Bijlage, DefaultAdmin)

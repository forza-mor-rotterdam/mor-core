from apps.instellingen.models import Instelling
from django.contrib import admin


class InstellingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "onderwerpen_basis_url",
    )


admin.site.register(Instelling, InstellingAdmin)

from apps.status.models import Status
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class MeldingStatusFilter(admin.SimpleListFilter):
    title = _("Melding status")
    parameter_name = "melding_status"

    def lookups(self, request, model_admin):
        return Status.NaamOpties.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(melding_voor_locatie__status__naam=self.value())
        return queryset

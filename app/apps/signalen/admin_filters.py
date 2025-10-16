from django.contrib import admin
from django.db.models import Count


class BijlagenAantalFilter(admin.SimpleListFilter):
    title = "Bijlagen aantal"
    parameter_name = "bijlagen_aantal"

    def lookups(self, request, model_admin):
        return (("bijlagen_aantal__gt", "1 of meer"),)

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.annotate(bijlagen_aantal=Count("bijlagen")).filter(
                **{self.value(): 0}
            )
        return queryset

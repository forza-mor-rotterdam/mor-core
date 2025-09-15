import ast
import importlib
import json

from apps.taken.models import Taakgebeurtenis, Taakopdracht, Taakstatus
from django.contrib import admin, messages
from django.db import transaction
from django.utils.safestring import mark_safe
from django_celery_beat.admin import PeriodicTaskAdmin
from django_celery_beat.models import PeriodicTask
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from .admin_filters import (
    AfgeslotenOpFilter,
    ResolutieFilter,
    StatusFilter,
    SyncedFilter,
    TaakStatusFilter,
    TaakUrlFilter,
    TitelFilter,
)


@admin.action(
    description="Verwijder geselecteerde taakgebeurtenissen met meldinggebeurtenis"
)
def action_verwijder_taakgebeurtenis_met_meldinggebeurtenis(
    modeladmin, request, queryset
):
    from apps.meldingen.models import Meldinggebeurtenis

    with transaction.atomic():
        deleted_meldinggebeurtenissen = Meldinggebeurtenis.objects.filter(
            taakgebeurtenis__in=queryset
        ).delete()
        deleted_taakgebeurtenissen = queryset.delete()

        transaction.on_commit(
            lambda: messages.info(
                request,
                f"Verwijderd met taakgebeurtenissen: {deleted_taakgebeurtenissen}, en verwijderd met meldinggebeurtenissen: {deleted_meldinggebeurtenissen}",
            )
        )


class TaakstatusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "naam",
        "taakopdracht",
    )
    raw_id_fields = ("taakopdracht",)
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
    )


class TaakgebeurtenisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "verwijderd_op",
        "taakstatus",
        "resolutie",
        "omschrijving_intern",
        "aangemaakt_op",
        "aangepast_op",
        "taakopdracht",
        "gebruiker",
        "meldinggebeurtenissen_aantal",
        "melding_uuid",
        "synced",
    )
    raw_id_fields = (
        "taakstatus",
        "taakopdracht",
    )
    readonly_fields = (
        "uuid",
        "aangemaakt_op",
        "aangepast_op",
    )
    search_fields = ("taakopdracht__melding__uuid", "taakopdracht__uuid", "uuid")
    date_hierarchy = "aangemaakt_op"
    actions = (action_verwijder_taakgebeurtenis_met_meldinggebeurtenis,)

    def melding_uuid(self, obj):
        return obj.taakopdracht.melding.uuid

    list_filter = (
        TaakUrlFilter,
        SyncedFilter,
        TaakStatusFilter,
    )

    def synced(self, obj):
        return obj.additionele_informatie.get("taak_url")

    def meldinggebeurtenissen_aantal(self, obj):
        return obj.meldinggebeurtenissen_voor_taakgebeurtenis.count()

    meldinggebeurtenissen_aantal.short_description = "Meldinggebeurtenissen aantal"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "taakstatus",
            "taakopdracht__melding",
        ).prefetch_related(
            "meldinggebeurtenissen_voor_taakgebeurtenis",
        )


@admin.action(description="Zet taak afgesloten_op voor afgesloten meldingen")
def action_set_taak_afgesloten_op_for_melding_afgesloten(modeladmin, request, queryset):
    for taakopdracht in queryset.all():
        if taakopdracht.melding.afgesloten_op and not taakopdracht.afgesloten_op:
            taakopdracht.afgesloten_op = taakopdracht.melding.afgesloten_op
            taakopdracht.save()


class TaakopdrachtAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uuid",
        "taaktype",
        "taak_url",
        "titel",
        "melding",
        "aangemaakt_op",
        "aangepast_op",
        "afgesloten_op",
        "verwijderd_op",
        "pretty_afhandeltijd",
        "melding__afgesloten_op",
        "pretty_status",
        "resolutie",
    )
    actions = (action_set_taak_afgesloten_op_for_melding_afgesloten,)
    list_filter = (
        StatusFilter,
        ResolutieFilter,
        AfgeslotenOpFilter,
        TitelFilter,
    )
    search_fields = [
        "id",
        "uuid",
        "melding__id",
        "melding__uuid",
    ]
    raw_id_fields = [
        "melding",
        "status",
    ]
    readonly_fields = (
        "uuid",
        "afhandeltijd",
        "pretty_afhandeltijd",
        "aangemaakt_op",
        "aangepast_op",
        "verwijderd_op",
        "afgesloten_op",
        "resolutie",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "uuid",
                    "titel",
                    "melding",
                    "applicatie",
                    "taaktype",
                    "status",
                    "resolutie",
                    "bericht",
                    "additionele_informatie",
                    "taak_url",
                )
            },
        ),
        (
            "Tijden",
            {
                "fields": (
                    "aangemaakt_op",
                    "aangepast_op",
                    "afgesloten_op",
                    "verwijderd_op",
                    "pretty_afhandeltijd",
                )
            },
        ),
    )

    def melding__afgesloten_op(self, obj):
        if obj.melding.afgesloten_op:
            return obj.melding.afgesloten_op
        else:
            return "-"

    def pretty_status(self, obj):
        if obj.status:
            return obj.status.naam
        else:
            return "-"

    pretty_status.short_description = "Status"
    pretty_status.admin_order_field = "status__naam"

    def pretty_afhandeltijd(self, obj):
        if obj.afhandeltijd:
            days = obj.afhandeltijd.days
            total_seconds = obj.afhandeltijd.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            remaining_hours = int(hours) % 24  # Remaining hours in the current day
            minutes, _ = divmod(remainder, 60)
            return f"{days} dagen, {remaining_hours} uur, {int(minutes)} minuten"
        else:
            return "-"

    pretty_afhandeltijd.short_description = "Afhandeltijd"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "melding",
            "status",
        ).prefetch_related("taakgebeurtenissen_voor_taakopdracht")


def retry_celery_task_admin_action(modeladmin, request, queryset):
    msg = ""
    for task_res in queryset:
        if task_res.status != "FAILURE":
            msg += f'{task_res.task_id} => Skipped. Not in "FAILURE" State<br>'
            continue
        try:
            task_actual_name = task_res.task_name.split(".")[-1]
            module_name = ".".join(task_res.task_name.split(".")[:-1])
            kwargs = json.loads(task_res.task_kwargs)
            if isinstance(kwargs, str):
                kwargs = kwargs.replace("'", '"')
                kwargs = json.loads(kwargs)
                if kwargs:
                    getattr(
                        importlib.import_module(module_name), task_actual_name
                    ).apply_async(kwargs=kwargs, task_id=task_res.task_id)
            if not kwargs:
                args = ast.literal_eval(ast.literal_eval(task_res.task_args))
                getattr(
                    importlib.import_module(module_name), task_actual_name
                ).apply_async(args, task_id=task_res.task_id)
            msg += f"{task_res.task_id} => Successfully sent to queue for retry.<br>"
        except Exception as ex:
            msg += f"{task_res.task_id} => Unable to process. Error: {ex}<br>"
    messages.info(request, mark_safe(msg))


retry_celery_task_admin_action.short_description = "Retry Task"


class CustomTaskResultAdmin(TaskResultAdmin):
    list_filter = (
        "status",
        "date_created",
        "date_done",
        # "periodic_task_name",
        "task_name",
    )
    actions = [
        retry_celery_task_admin_action,
    ]


class CustomPeriodicTaskAdmin(PeriodicTaskAdmin):
    raw_id_fields = ("clocked",)


admin.site.unregister(TaskResult)
admin.site.register(TaskResult, CustomTaskResultAdmin)

admin.site.unregister(PeriodicTask)
admin.site.register(PeriodicTask, CustomPeriodicTaskAdmin)


admin.site.register(Taakstatus, TaakstatusAdmin)
admin.site.register(Taakopdracht, TaakopdrachtAdmin)
admin.site.register(Taakgebeurtenis, TaakgebeurtenisAdmin)

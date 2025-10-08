from apps.taken.models import Taakopdracht
from celery import states
from django.db.models import Q
from django_filters import rest_framework as filters

STATUS_CHOICES = (
    (states.PENDING, states.PENDING),
    (states.STARTED, states.STARTED),
    (states.RETRY, states.RETRY),
    (states.FAILURE, states.FAILURE),
    (states.SUCCESS, states.SUCCESS),
    ("geen_task", "geen_task"),
)


class TaakopdrachtFilter(filters.FilterSet):
    melding_afgesloten_op_gte = filters.DateTimeFilter(
        field_name="melding__afgesloten_op", lookup_expr="gte"
    )
    melding_afgesloten_op_gt = filters.DateTimeFilter(
        field_name="melding__afgesloten_op", lookup_expr="gt"
    )
    melding_afgesloten_op_lte = filters.DateTimeFilter(
        field_name="melding__afgesloten_op", lookup_expr="lte"
    )
    melding_afgesloten_op_lt = filters.DateTimeFilter(
        field_name="melding__afgesloten_op", lookup_expr="lt"
    )
    aangemaakt_op_gte = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="gte"
    )
    aangemaakt_op_gt = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="gt"
    )
    aangemaakt_op_lte = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="lte"
    )
    aangemaakt_op_lt = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="lt"
    )
    afgesloten_op_gte = filters.DateTimeFilter(
        field_name="afgesloten_op", lookup_expr="gte"
    )
    afgesloten_op_gt = filters.DateTimeFilter(
        field_name="afgesloten_op", lookup_expr="gt"
    )
    afgesloten_op_lte = filters.DateTimeFilter(
        field_name="afgesloten_op", lookup_expr="lte"
    )
    afgesloten_op_lt = filters.DateTimeFilter(
        field_name="afgesloten_op", lookup_expr="lt"
    )
    resolutie = filters.CharFilter(field_name="resolutie")
    taaktype = filters.CharFilter(field_name="taaktype")
    taaktype_startswith = filters.CharFilter(
        field_name="taaktype", lookup_expr="startswith"
    )
    has_no_taak_url = filters.BooleanFilter(field_name="taak_url", lookup_expr="isnull")
    task_taak_aanmaken_status = filters.MultipleChoiceFilter(
        choices=STATUS_CHOICES,
        method="get_task_taak_aanmaken_status",
    )

    def get_task_taak_aanmaken_status(self, queryset, name, value):
        if value:
            if "geen_task" in value:
                Q(task_taak_aanmaken__isnull=True)
            status_filters = [
                Q(task_taak_aanmaken__status=f)
                if f != "geen_task"
                else Q(task_taak_aanmaken__isnull=True)
                for f in value
            ]
            query = status_filters.pop()
            for item in status_filters:
                query |= item
            queryset = queryset.filter(query)
        return queryset

    class Meta:
        model = Taakopdracht
        fields = [
            "melding",
        ]

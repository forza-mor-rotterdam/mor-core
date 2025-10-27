from apps.applicaties.models import Applicatie
from django_filters import rest_framework as filters


class ApplicatieFilterSet(filters.FilterSet):
    applicatie_type = filters.MultipleChoiceFilter(
        choices=Applicatie.ApplicatieTypes.choices,
    )

    class Meta:
        model = Applicatie
        fields = [
            "applicatie_type",
        ]

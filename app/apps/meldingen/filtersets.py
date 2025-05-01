import logging
from collections import OrderedDict
from typing import List, Tuple

from apps.aliassen.models import OnderwerpAlias
from apps.locatie.models import Locatie
from apps.meldingen.models import Melding
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.postgres.search import TrigramSimilarity
from django.db import models
from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Greatest
from django.forms.fields import CharField, MultipleChoiceField
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import filters as rest_filters
from rest_framework.filters import SearchFilter
from rest_framework.settings import api_settings

logger = logging.getLogger(__name__)


class DjangoPreFilterBackend(filters.DjangoFilterBackend):
    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """
        filterset_class = getattr(view, "pre_filterset_class", None)

        if filterset_class:
            filterset_model = filterset_class._meta.model

            # FilterSets do not need to specify a Meta class
            if filterset_model and queryset is not None:
                assert issubclass(
                    queryset.model, filterset_model
                ), "FilterSet model %s does not match queryset model %s" % (
                    filterset_model,
                    queryset.model,
                )

            return filterset_class

        return None


class MultipleValueField(MultipleChoiceField):
    def __init__(self, *args, field_class, **kwargs):
        self.inner_field = field_class()
        super().__init__(*args, **kwargs)

    def valid_value(self, value):
        return self.inner_field.validate(value)

    def clean(self, values):
        return values and [self.inner_field.clean(value) for value in values]


class MultipleValueFilter(filters.Filter):
    field_class = MultipleValueField

    def __init__(self, *args, field_class, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        super().__init__(*args, field_class=field_class, **kwargs)


class PreFilterFilterSet(filters.FilterSet):
    pre_filter = False

    @classmethod
    def get_filters(cls):
        filters = super().get_filters()
        if cls.pre_filter:
            filters = OrderedDict([(f"pre_{k}", v) for k, v in filters.items()])
        return filters


class BasisFilter(PreFilterFilterSet):
    aangemaakt_op_gte = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="gte"
    )
    aangemaakt_op_gt = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="gt"
    )
    aangepast_op_gt = filters.DateTimeFilter(
        field_name="aangepast_op", lookup_expr="gt"
    )
    aangepast_op_gte = filters.DateTimeFilter(
        field_name="aangepast_op", lookup_expr="gte"
    )
    aangemaakt_op_lte = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="lte"
    )
    aangemaakt_op_lt = filters.DateTimeFilter(
        field_name="aangemaakt_op", lookup_expr="lt"
    )
    aangepast_op_lt = filters.DateTimeFilter(
        field_name="aangepast_op", lookup_expr="lt"
    )
    aangepast_op_lte = filters.DateTimeFilter(
        field_name="aangepast_op", lookup_expr="lte"
    )


class MeldingFilter(BasisFilter):
    origineel_aangemaakt_gte = filters.DateTimeFilter(
        field_name="origineel_aangemaakt", lookup_expr="gte"
    )
    origineel_aangemaakt_gt = filters.DateTimeFilter(
        field_name="origineel_aangemaakt", lookup_expr="gt"
    )
    origineel_aangemaakt_lte = filters.DateTimeFilter(
        field_name="origineel_aangemaakt", lookup_expr="lte"
    )
    origineel_aangemaakt_lt = filters.DateTimeFilter(
        field_name="origineel_aangemaakt", lookup_expr="lt"
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

    omschrijving = filters.CharFilter(method="get_omschrijving")
    q = filters.CharFilter(method="get_q")

    actieve_meldingen = filters.BooleanFilter(method="get_actieve_meldingen")
    onderwerp = MultipleValueFilter(field_class=CharField, method="get_onderwerpen")
    onderwerp_url = MultipleValueFilter(
        field_class=CharField, method="get_onderwerp_urls"
    )
    status = MultipleValueFilter(field_class=CharField, method="get_statussen")
    buurt = MultipleValueFilter(field_class=CharField, method="get_buurt")
    wijk = MultipleValueFilter(field_class=CharField, method="get_wijk")
    begraafplaats = MultipleValueFilter(
        field_class=CharField, method="get_begraafplaatsen"
    )
    begraafplaats_vak = filters.CharFilter(
        field_name="locaties_voor_melding__vak", lookup_expr="icontains"
    )
    begraafplaats_grafnummer = filters.CharFilter(
        field_name="locaties_voor_melding__grafnummer", lookup_expr="icontains"
    )
    begraafplaats_grafnummer_gte = filters.NumberFilter(
        method="get_begraafplaats_grafnummer"
    )
    begraafplaats_grafnummer_gt = filters.NumberFilter(
        method="get_begraafplaats_grafnummer"
    )
    begraafplaats_grafnummer_lte = filters.NumberFilter(
        method="get_begraafplaats_grafnummer"
    )
    begraafplaats_grafnummer_lt = filters.NumberFilter(
        method="get_begraafplaats_grafnummer"
    )
    within = filters.CharFilter(method="get_within")
    urgentie = filters.NumberFilter(
        field_name="urgentie",
    )
    urgentie_gt = filters.NumberFilter(field_name="urgentie", lookup_expr="gt")
    urgentie_gte = filters.NumberFilter(field_name="urgentie", lookup_expr="gte")
    urgentie_lt = filters.NumberFilter(field_name="urgentie", lookup_expr="lt")
    urgentie_lte = filters.NumberFilter(field_name="urgentie", lookup_expr="lte")

    def get_within(self, queryset, name, value):
        """
        ./?within=lat:51.924392,d:100,lon:4.477738
        """
        try:
            d = {
                n: float(value.split(f"{n}:")[1].split(",")[0])
                for n in ["lat", "lon", "d"]
            }
        except Exception:
            logger.warning(f"Warning: within syntax not ok: {value}")
            return queryset
        locaties = Locatie.objects.filter(
            melding=OuterRef("pk"),
            geometrie__isnull=False,
        ).order_by("-gewicht")
        return queryset.annotate(geometrie=locaties.values("geometrie")[:1]).filter(
            geometrie__distance_lt=(
                Point(d["lon"], d["lat"]),
                D(m=d["d"]),
            )
        )

    def get_begraafplaats_grafnummer(self, queryset, name, value):
        if value:
            valid_lookup_expr = ["gt", "gte", "lt", "lte"]
            lookup_expr = (
                name.rsplit("_", 1)[1] if name.rsplit("_", 1) else valid_lookup_expr[0]
            )
            lookup_expr = (
                lookup_expr
                if lookup_expr in valid_lookup_expr
                else valid_lookup_expr[0]
            )
            return queryset.filter(
                locaties_voor_melding__grafnummer__regex="^[0-9]+$"
            ).filter(Q(**{f"locaties_voor_melding__grafnummer__{lookup_expr}": value}))
        return queryset

    def get_omschrijving(self, queryset, name, value):
        if value:
            qs = (
                queryset.annotate(
                    similarity=TrigramSimilarity("omschrijving", str(value))
                )
                .filter(similarity__gt=0.3)
                .order_by("-similarity")
            )
            return qs
        return queryset

    # Er kan op meerdere komma separated zoektermen gezocht worden
    def get_q(self, queryset, name, value):
        if value:
            search_terms = value.split(",")
            cleaned_search_terms = [
                "".join(
                    [
                        char
                        for char in term.strip()
                        if char not in ["*", "(", ")", "?", "[", "]", "{", "}", "\\"]
                    ]
                )
                for term in search_terms
            ]
            cleaned_search_terms = [term for term in cleaned_search_terms if term]

            combined_q = Q()
            for term in cleaned_search_terms:
                combined_q &= Q(zoek_tekst__icontains=term)

            return queryset.filter(combined_q).distinct()

        return queryset

    def get_buurt(self, queryset, name, value):
        if value:
            return queryset.filter(
                locaties_voor_melding__buurtnaam__in=value,
                locaties_voor_melding__primair=True,
            ).distinct()
        return queryset

    def get_wijk(self, queryset, name, value):
        if value:
            return queryset.filter(
                locaties_voor_melding__wijknaam__in=value,
                locaties_voor_melding__primair=True,
            ).distinct()
        return queryset

    def get_begraafplaatsen(self, queryset, name, value):
        if value:
            return queryset.filter(
                locaties_voor_melding__begraafplaats__in=value,
            ).distinct()
        return queryset

    def get_statussen(self, queryset, name, value):
        if value:
            return queryset.filter(status__naam__in=value).distinct()
        return queryset

    def get_onderwerpen(self, queryset, name, value):
        if value:
            return queryset.filter(onderwerpen__in=value).distinct()
        return queryset

    def get_onderwerp_urls(self, queryset, name, value):
        if value:
            return queryset.filter(onderwerpen__bron_url__in=value).distinct()
        return queryset

    def get_actieve_meldingen(self, queryset, name, value):
        return queryset.filter(afgesloten_op__isnull=value)

    class Meta:
        model = Melding
        fields = [
            "aangemaakt_op",
            "aangepast_op",
            "origineel_aangemaakt",
            "afgesloten_op",
        ]


class MeldingPreFilter(MeldingFilter):
    pre_filter = True

    class Meta:
        model = Melding
        fields = [
            "aangemaakt_op",
            "aangepast_op",
            "origineel_aangemaakt",
            "afgesloten_op",
        ]


class RelatedOrderingFilter(rest_filters.OrderingFilter):
    _max_related_depth = 3

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            straatnaam_ordering = ["straatnaam", "-straatnaam"]
            onderwerp_ordering = ["onderwerp", "-onderwerp"]
            if list(set(ordering) & set(onderwerp_ordering)):
                onderwerpen = OnderwerpAlias.objects.filter(
                    meldingen_voor_onderwerpen=OuterRef("pk")
                )
                queryset = queryset.annotate(
                    onderwerp=Subquery(onderwerpen.values("response_json__name")[:1])
                )
            if list(set(ordering) & set(straatnaam_ordering)):
                locaties = Locatie.objects.filter(
                    melding=OuterRef("pk"),
                ).order_by("-gewicht")
                queryset = queryset.annotate(
                    straatnaam=Subquery(locaties.values("straatnaam")[:1])
                )
            qs = queryset.order_by(*ordering)
            return qs

        return queryset

    @staticmethod
    def _get_verbose_name(field: models.Field, non_verbose_name: str) -> str:
        return (
            field.verbose_name
            if hasattr(field, "verbose_name")
            else non_verbose_name.replace("_", " ")
        )

    def _retrieve_all_related_fields(
        self, fields: Tuple[models.Field], model: models.Model, depth: int = 0
    ) -> List[tuple]:
        valid_fields = []
        if depth > self._max_related_depth:
            return valid_fields
        for field in fields:
            if field.related_model and field.related_model != model:
                rel_fields = self._retrieve_all_related_fields(
                    field.related_model._meta.get_fields(),
                    field.related_model,
                    depth + 1,
                )
                for rel_field in rel_fields:
                    valid_fields.append(
                        (
                            f"{field.name}__{rel_field[0]}",
                            self._get_verbose_name(field, rel_field[1]),
                        )
                    )
            else:
                valid_fields.append(
                    (
                        field.name,
                        self._get_verbose_name(field, field.name),
                    )
                )
        return valid_fields

    def get_valid_fields(
        self, queryset: models.QuerySet, view, context: dict = None
    ) -> List[tuple]:
        valid_fields = getattr(view, "ordering_fields", self.ordering_fields)
        if valid_fields != "__all_related__":
            if not context:
                context = {}
            valid_fields = super().get_valid_fields(queryset, view, context)
        else:
            valid_fields = [
                *self._retrieve_all_related_fields(
                    queryset.model._meta.get_fields(),
                    queryset.model,
                ),
                *[(key, key.title().split("__")) for key in queryset.query.annotations],
            ]
        return valid_fields


class TrigramSimilaritySearchFilter(SearchFilter):
    search_param = api_settings.SEARCH_PARAM
    template = "rest_framework/filters/search.html"
    search_title = _("Search")
    search_description = _("A search term.")

    def get_trigram_similarity(self, view, request):
        return getattr(view, "trigram_similarity", 0.3)

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.query_params.get(self.search_param, "")
        params = params.replace("\x00", "")  # strip null characters
        params = params.replace(",", " ")
        return params.split()

    def get_search_fields(self, view, request):
        """
        Search fields are obtained from the view, but the request is always
        passed to this method. Sub-classes can override this method to
        dynamically change the search fields based on request content.
        """
        return getattr(view, "search_fields", [])

    def filter_queryset(self, request, queryset, view):
        trigram_similarity = self.get_trigram_similarity(view, request)
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)

        # if no search_terms return
        if not search_terms:
            return queryset

        # make conditions
        conditions = []
        for search_term in search_terms:
            conditions.extend(
                [TrigramSimilarity(field, search_term) for field in search_fields]
            )

        # take the greatest similarity from all conditions
        # and annotate as similarity
        return queryset.annotate(similarity=Greatest(*conditions)).filter(
            similarity__gte=trigram_similarity
        )

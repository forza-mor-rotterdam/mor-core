import logging

from apps.meldingen.filtersets import (
    MeldingFilter,
    RelatedOrderingFilter,
    SpecificatieFilterSet,
)
from apps.meldingen.models import Melding, Meldinggebeurtenis, Specificatie
from apps.meldingen.serializers import (
    MeldingAantallenSerializer,
    MeldingDetailSerializer,
    MeldingGebeurtenisAfhandelenSerializer,
    MeldinggebeurtenisSerializer,
    MeldingGebeurtenisStatusSerializer,
    MeldingGebeurtenisUrgentieSerializer,
    MeldingSerializer,
    SpecificatieSerializer,
)
from apps.taken.serializers import (
    TaakopdrachtNotificatieSaveSerializer,
    TaakopdrachtNotificatieSerializer,
    TaakopdrachtSerializer,
    TaakopdrachtVerwijderenSerializer,
)
from config.context import db
from django.conf import settings
from django.http import Http404, JsonResponse
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class MeldinggebeurtenisViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    lookup_field = "uuid"
    queryset = Meldinggebeurtenis.objects.all()

    serializer_class = MeldinggebeurtenisSerializer


@extend_schema(
    parameters=[
        OpenApiParameter("omschrijving", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("onderwerp", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("begraafplaats", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("begraafplaats_vak", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter(
            "begraafplaats_grafnummer", OpenApiTypes.STR, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "begraafplaats_grafnummer_gte", OpenApiTypes.INT, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "begraafplaats_grafnummer_gt", OpenApiTypes.INT, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "begraafplaats_grafnummer_lte", OpenApiTypes.INT, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "begraafplaats_grafnummer_lt", OpenApiTypes.INT, OpenApiParameter.QUERY
        ),
        OpenApiParameter("meta__categorie", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter(
            "aangemaakt_op_gte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangemaakt_op_gt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangemaakt_op_lte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangemaakt_op_lt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangepast_op_gte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangepast_op_gt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangepast_op_lte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "aangepast_op_lt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "origineel_aangemaakt_gte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "origineel_aangemaakt_gt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "origineel_aangemaakt_lte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "origineel_aangemaakt_lt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "afgesloten_op_gte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "afgesloten_op_gt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "afgesloten_op_lte", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "afgesloten_op_lt", OpenApiTypes.DATETIME, OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            "actieve_meldingen", OpenApiTypes.BOOL, OpenApiParameter.QUERY
        ),
    ]
)
class MeldingViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "uuid"
    queryset = (
        Melding.objects.select_related(
            "status",
        )
        .prefetch_related(
            "onderwerpen",
            "thumbnail_afbeelding",
            "referentie_locatie",
            "signalen_voor_melding",
            "taakopdrachten_voor_melding__status",
        )
        .all()
    )
    prefiltered_queryset = None
    serializer_class = MeldingSerializer
    serializer_detail_class = MeldingDetailSerializer
    filter_backends = (
        filters.DjangoFilterBackend,
        RelatedOrderingFilter,
    )
    ordering_fields = [
        "id",
        "-id",
        "straatnaam",
        "-straatnaam",
        "referentie_locatie__straatnaam",
        "-referentie_locatie__straatnaam",
        "referentie_locatie__buurtnaam",
        "-referentie_locatie__buurtnaam",
        "locaties_voor_melding__buurtnaam",
        "-locaties_voor_melding__buurtnaam",
        "locaties_voor_melding__wijknaam",
        "-locaties_voor_melding__wijknaam",
        # "onderwerp",
        # "-onderwerp",
        "referentie_locatie__vak",
        "-referentie_locatie__vak",
        "referentie_locatie__grafnummer",
        "-referentie_locatie__grafnummer",
        "referentie_locatie__begraafplaats",
        "-referentie_locatie__begraafplaats",
        "origineel_aangemaakt",
        "-origineel_aangemaakt",
        "status__naam",
        "-status__naam",
        "urgentie",
        "-urgentie",
    ]
    filterset_class = MeldingFilter

    def get_queryset(self):
        if self.action == "retrieve":
            return (
                Melding.objects.select_related(
                    "status",
                )
                .prefetch_related(
                    "bijlagen",
                    "signalen_voor_melding__bijlagen",
                    "meldinggebeurtenissen_voor_melding__bijlagen",
                    "meldinggebeurtenissen_voor_melding__status",
                    "meldinggebeurtenissen_voor_melding__locatie",
                    "meldinggebeurtenissen_voor_melding__taakgebeurtenis__taakopdracht",
                    "meldinggebeurtenissen_voor_melding__taakgebeurtenis__bijlagen",
                    "meldinggebeurtenissen_voor_melding__taakgebeurtenis__taakstatus",
                    "taakopdrachten_voor_melding__applicatie",
                    "taakopdrachten_voor_melding__status",
                    "taakopdrachten_voor_melding__taakgebeurtenissen_voor_taakopdracht__bijlagen",
                    "taakopdrachten_voor_melding__taakgebeurtenissen_voor_taakopdracht__taakstatus",
                    "locaties_voor_melding",
                    "signalen_voor_melding__locaties_voor_signaal",
                )
                .all()
            )
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return self.serializer_detail_class
        return super().get_serializer_class()

    def list(self, request):
        with db(settings.READONLY_DATABASE_KEY):
            queryset = self.filter_queryset(self.get_queryset())

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

    def retrieve(self, request, uuid=None):
        with db(settings.READONLY_DATABASE_KEY):
            return super().retrieve(request, uuid)

    @extend_schema(
        description="Verander de status van een melding",
        request=MeldingGebeurtenisStatusSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(detail=True, methods=["patch"], url_path="status-aanpassen")
    def status_aanpassen(self, request, uuid):
        melding = self.get_object()
        data = {}
        data.update(request.data)
        data["melding"] = melding.id
        data["status"]["melding"] = melding.id
        data["gebeurtenis_type"] = Meldinggebeurtenis.GebeurtenisType.STATUS_WIJZIGING
        serializer = MeldingGebeurtenisStatusSerializer(
            data=data,
            context={"request": request},
        )
        if serializer.is_valid():
            Melding.acties.status_aanpassen(serializer, self.get_object())

            serializer = MeldingDetailSerializer(
                self.get_object(), context={"request": request}
            )
            return Response(serializer.data)
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Melding afhandelen",
        request=MeldingGebeurtenisAfhandelenSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="afhandelen",
        name="afhandelen",
        filter_backends=(),
        pagination_class=None,
        filterset_class=None,
    )
    def afhandelen(self, request, uuid):
        melding = self.get_object()
        if melding.afgesloten_op and melding.resolutie:
            return Response(
                data={"warning": f"Melding '{uuid}', is al afgesloten!"},
            )
        serializer = MeldingGebeurtenisAfhandelenSerializer(
            data=request.data,
            context={
                "request": request,
                "melding": melding,
            },
        )
        if serializer.is_valid():
            Melding.acties.status_aanpassen(serializer, self.get_object())
            serializer = MeldingDetailSerializer(
                self.get_object(),
                context={
                    "request": request,
                },
            )
            return Response(serializer.data)
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Rapporteert dat een taak gewijzigd is aan de taakapplicatie kant. Geeft uitsluitend aan dat er een wijziging is. MorCore haalt de taak vervolgens op bij de taakapplicatie.",
        request=TaakopdrachtNotificatieSerializer,
        responses={status.HTTP_200_OK: TaakopdrachtNotificatieSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="taakopdracht/(?P<taakopdracht_uuid>[^/.]+)/notificatie",
        name="taakopdracht-notificatie",
    )
    def taakopdracht_notificatie(self, request, uuid, taakopdracht_uuid):
        from apps.taken.models import Taakopdracht

        melding = self.get_object()
        try:
            taakopdracht = melding.taakopdrachten_voor_melding.get(
                uuid=taakopdracht_uuid
            )
        except Taakopdracht.DoesNotExist:
            raise Http404("De taakopdracht is niet gevonden!")

        data = {}
        data.update(request.data)

        if taakopdracht.verwijderd_op:
            return Response({})
        if taakopdracht.is_voltooid and not data.get("resolutie_opgelost_herzien"):
            return Response({})

        if data.get("taakstatus"):
            data["taakstatus"]["taakopdracht"] = taakopdracht.id
            if data["taakstatus"]["naam"] == taakopdracht.status.naam:
                logger.warning(
                    f"taakopdracht_notificatie: de nieuwe status mag niet hetzelfde zijn als de huidige, taakopdracht_id={taakopdracht.id}"
                )
                return Response({})

        serializer = TaakopdrachtNotificatieSaveSerializer(
            data=data,
        )
        if serializer.is_valid():
            Melding.acties.taakopdracht_notificatie(taakopdracht, data)
        logger.warning(
            f"taakopdracht_notificatie: serializer.errors={serializer.errors}"
        )
        return Response({})

    @extend_schema(
        description="Markeert de taakopdracht in MorCore als verwijderd en stuurt de delete actie naar taakapplicatie.",
        request=TaakopdrachtVerwijderenSerializer,
        responses={status.HTTP_200_OK: TaakopdrachtVerwijderenSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path="taakopdracht/(?P<taakopdracht_uuid>[^/.]+)",
    )
    def taakopdracht_verwijderen(self, request, uuid, taakopdracht_uuid):
        from apps.taken.models import Taakopdracht

        melding = self.get_object()
        try:
            taakopdracht = melding.taakopdrachten_voor_melding.get(
                uuid=taakopdracht_uuid
            )
        except Taakopdracht.DoesNotExist:
            raise Http404("De taakopdracht is niet gevonden!")

        if taakopdracht.verwijderd_op:
            raise serializers.ValidationError("Deze taakopdracht is al verwijderd")

        Melding.acties.taakopdracht_verwijderen(
            taakopdracht, request.GET.get("gebruiker")
        )

        return Response({})

    @extend_schema(
        description="Melding heropenen",
        request=MeldingGebeurtenisStatusSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(detail=True, methods=["patch"], url_path="heropenen")
    def heropenen(self, request, uuid):
        melding = self.get_object()
        data = {}
        data.update(request.data)
        data["melding"] = melding.id
        data["status"]["melding"] = melding.id
        data["gebeurtenis_type"] = Meldinggebeurtenis.GebeurtenisType.MELDING_HEROPEND
        serializer = MeldingGebeurtenisStatusSerializer(
            data=data,
            context={"request": request},
        )
        if serializer.is_valid():
            Melding.acties.status_aanpassen(serializer, self.get_object(), heropen=True)

            serializer = MeldingDetailSerializer(
                self.get_object(), context={"request": request}
            )
            return Response(serializer.data)
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Verander de urgentie van een melding",
        request=MeldingGebeurtenisUrgentieSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(detail=True, methods=["patch"], url_path="urgentie-aanpassen")
    def urgentie_aanpassen(self, request, uuid):
        melding = self.get_object()
        data = {}
        data.update(request.data)
        data["melding"] = melding.id
        data["gebeurtenis_type"] = Meldinggebeurtenis.GebeurtenisType.URGENTIE_AANGEPAST
        serializer = MeldingGebeurtenisUrgentieSerializer(
            data=data,
            context={"request": request},
        )
        if serializer.is_valid():
            Melding.acties.urgentie_aanpassen(serializer, self.get_object())

            serializer = MeldingDetailSerializer(
                self.get_object(), context={"request": request}
            )
            return Response(serializer.data)
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Gebeurtenis voor een melding toevoegen",
        request=MeldinggebeurtenisSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="gebeurtenis-toevoegen",
        serializer_class=MeldinggebeurtenisSerializer,
    )
    def gebeurtenis_toevoegen(self, request, uuid):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            Melding.acties.gebeurtenis_toevoegen(serializer, self.get_object())

            serializer = MeldingDetailSerializer(
                self.get_object(), context={"request": request}
            )
            return Response(serializer.data)
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Taakopdracht voor een melding toevoegen",
        request=TaakopdrachtSerializer,
        responses={status.HTTP_200_OK: TaakopdrachtSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="taakopdracht",
        serializer_class=TaakopdrachtSerializer,
        name="taakopdracht-aanmaken",
    )
    def taakopdracht_aanmaken(self, request, uuid):
        melding = self.get_object()
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            taakopdracht = Melding.acties.taakopdracht_aanmaken(
                serializer, melding, request
            )

            serializer = TaakopdrachtSerializer(
                taakopdracht, context={"request": request}
            )
            return Response(serializer.data, status.HTTP_201_CREATED)
        logger.warning(f"taakopdracht_aanmaken: {serializer.errors}")
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @extend_schema(
        description="Locatie aanmaken voor een melding",
        request=MeldinggebeurtenisSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="locatie-aanmaken",
        serializer_class=MeldinggebeurtenisSerializer,
    )
    def locatie_aanmaken(self, request, uuid):
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )
        try:
            serializer.is_valid(raise_exception=True)
            Melding.acties.gebeurtenis_toevoegen(serializer, self.get_object())

            serializer_data = MeldingDetailSerializer(
                self.get_object(), context={"request": request}
            ).data

            # Use JsonResponse for both success and error cases
            return Response(serializer_data, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            logger.error(e)
            # Return a JsonResponse with the error details
            return JsonResponse(
                {"error": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            # Return a JsonResponse with the specific error message
            logger.error(e)
            return JsonResponse(
                {"error": "An internal server error occurred!"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        description="Nieuwe melding aantallen per wijk en onderwerp",
        responses={status.HTTP_200_OK: MeldingAantallenSerializer(many=True)},
        parameters=None,
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="aantallen",
        serializer_class=MeldingAantallenSerializer,
    )
    def nieuwe_meldingen(self, request):
        with db(settings.READONLY_DATABASE_KEY):
            serializer = MeldingAantallenSerializer(
                self.filter_queryset(self.get_queryset()).nieuwe_meldingen(),
                context={"request": request},
                many=True,
            )
        return Response(serializer.data)


@extend_schema(
    parameters=[
        OpenApiParameter("naam", OpenApiTypes.STR, OpenApiParameter.QUERY),
    ]
)
class SpecificatieViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    queryset = Specificatie.objects.all()
    serializer_class = SpecificatieSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = SpecificatieFilterSet

    def destroy(self, request, *args, **kwargs):
        specificatie = self.get_object()
        specificatie.verwijderd_op = timezone.now()
        specificatie.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

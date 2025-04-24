import logging

from apps.locatie.models import Locatie
from apps.meldingen.filtersets import MeldingFilter, RelatedOrderingFilter
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.meldingen.serializers import (
    MeldingAantallenSerializer,
    MeldingDetailSerializer,
    MeldinggebeurtenisSerializer,
    MeldingGebeurtenisStatusSerializer,
    MeldingGebeurtenisUrgentieSerializer,
    MeldingSerializer,
)
from apps.taken.serializers import (
    TaakopdrachtNotificatieSaveSerializer,
    TaakopdrachtNotificatieSerializer,
    TaakopdrachtSerializer,
    TaakopdrachtVerwijderenSerializer,
)
from config.context import db
from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404, JsonResponse
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
            Prefetch(
                "locaties_voor_melding",
                queryset=Locatie.objects.exclude(locatie_type="lichtmast"),
            ),
            "signalen_voor_melding__bijlagen",
            "bijlagen",
            "meldinggebeurtenissen_voor_melding__bijlagen",
            "meldinggebeurtenissen_voor_melding__taakgebeurtenis__bijlagen",
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
    ordering_fields = "__all_related__"
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
            return super().list(request)

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
        data = {"melding": melding.id}
        data.update(request.data)
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
        description="Rapporteert dat een taak gewijzigd is aan de taakapplicatie kant. Geeft uitsluitend aan dat er een wijziging is. MorCore haalt de taak vervolgens op bij de taakapplicatie.",
        request=TaakopdrachtNotificatieSerializer,
        responses={status.HTTP_200_OK: TaakopdrachtNotificatieSerializer},
        parameters=None,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="taakopdracht/(?P<taakopdracht_uuid>[^/.]+)/notificatie",
        permission_classes=(),
    )
    def taakopdracht_notificatie(self, request, uuid, taakopdracht_uuid):
        from apps.taken.models import Taakopdracht, Taakstatus

        melding = self.get_object()
        try:
            taakopdracht = melding.taakopdrachten_voor_melding.get(
                uuid=taakopdracht_uuid
            )
        except Taakopdracht.DoesNotExist:
            raise Http404("De taakopdracht is niet gevonden!")

        data = {}
        data.update(request.data)

        IS_VOLTOOID_MET_FEEDBACK = (
            taakopdracht.status.naam == Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK
        )
        IS_VOLTOOID_MET_HERZIEN = (
            taakopdracht.status.naam == Taakstatus.NaamOpties.VOLTOOID
            and not request.data.get("resolutie_opgelost_herzien", False)
        )
        IS_VORIGE_STATUS = taakopdracht.status.naam == data.get("taakstatus", {}).get(
            "naam"
        )
        if (
            taakopdracht.verwijderd_op
            or IS_VOLTOOID_MET_FEEDBACK
            or IS_VOLTOOID_MET_HERZIEN
            or IS_VORIGE_STATUS
        ):
            return Response({})

        print(data)
        if data.get("taakstatus"):
            data["taakstatus"]["taakopdracht"] = taakopdracht.id
        print(data)
        serializer = TaakopdrachtNotificatieSaveSerializer(
            data=data,
            context={"request": request},
        )
        if serializer.is_valid():
            print("is valid")
            Melding.acties.taakopdracht_notificatie(taakopdracht, serializer)
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

        taakgebeurtenis = Melding.acties.taakopdracht_verwijderen(
            taakopdracht, gebruiker=request.GET.get("gebruiker")
        )

        serializer = TaakopdrachtVerwijderenSerializer(
            taakgebeurtenis, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        description="Melding heropenen",
        request=MeldingGebeurtenisStatusSerializer,
        responses={status.HTTP_200_OK: MeldingDetailSerializer},
        parameters=None,
    )
    @action(detail=True, methods=["patch"], url_path="heropenen")
    def heropenen(self, request, uuid):
        melding = self.get_object()
        data = {"melding": melding.id}
        data.update(request.data)
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
        data = {"melding": melding.id}
        data.update(request.data)
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

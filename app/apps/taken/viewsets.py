from apps.meldingen.models import Melding
from apps.taken.models import Taakgebeurtenis, Taakopdracht
from apps.taken.serializers import (
    TaakgebeurtenisSerializer,
    TaakgebeurtenisStatusSerializer,
    TaakopdrachtSerializer,
)
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class TaakgebeurtenisViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Taakgebeurtenis viewset
    """

    lookup_field = "uuid"
    queryset = Taakgebeurtenis.objects.all()

    serializer_class = TaakgebeurtenisSerializer


class TaakopdrachtViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Taakopdracht
    """

    lookup_field = "uuid"
    queryset = Taakopdracht.objects.all()

    serializer_class = TaakopdrachtSerializer

    @extend_schema(
        description="Verander de status van een taak",
        request=TaakgebeurtenisStatusSerializer,
        responses={status.HTTP_200_OK: TaakopdrachtSerializer},
        parameters=None,
    )
    @action(detail=True, methods=["patch"], url_path="status-aanpassen")
    def status_aanpassen(self, request, uuid):
        taakopdracht = self.get_object()
        data = {}
        data.update(request.data)
        data["taakstatus"]["taakopdracht"] = taakopdracht.id
        serializer = TaakgebeurtenisStatusSerializer(
            data=data,
            context={"request": request},
        )
        if serializer.is_valid():
            externr_niet_opgelost = request.data.get("externr_niet_opgelost", False)
            Melding.acties.taakopdracht_status_aanpassen(
                serializer,
                taakopdracht,
                request=request,
                externr_niet_opgelost=externr_niet_opgelost,
            )

            serializer = TaakopdrachtSerializer(
                self.get_object(), context={"request": request}
            )
            return Response(serializer.data)
        return Response(
            data=serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

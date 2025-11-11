# from apps.meldingen.serializers import BijlageSerializer
from apps.bijlagen.serializers import BijlageSerializer
from apps.taken.models import Taakgebeurtenis, Taakopdracht, Taakstatus
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework import serializers
from rest_framework.reverse import reverse


class TaakstatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taakstatus
        fields = (
            "naam",
            "aangemaakt_op",
            "taakopdracht",
        )


class TaakgebeurtenisLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()
    taakopdracht = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:taakgebeurtenis-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_taakopdracht(self, obj):
        return reverse(
            "v1:taakopdracht-detail",
            kwargs={"uuid": obj.taakopdracht.uuid},
            request=self.context.get("request"),
        )


class TaakgebeurtenisSerializer(serializers.ModelSerializer):
    _links = TaakgebeurtenisLinksSerializer(source="*", read_only=True)
    bijlagen = BijlageSerializer(many=True, required=False)
    taakstatus = TaakstatusSerializer(required=False)

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "_links",
            "aangemaakt_op",
            "verwijderd_op",
            "bijlagen",
            "taakstatus",
            "resolutie",
            "omschrijving_intern",
            "taakopdracht",
            "gebruiker",
            "additionele_informatie",
        )
        read_only_fields = (
            "_links",
            "aangemaakt_op",
            "verwijderd_op",
            "bijlagen",
            "taakstatus",
            "resolutie",
            "omschrijving_intern",
            "taakopdracht",
            "additionele_informatie",
        )


class TaakgebeurtenisBijlagenSerializer(serializers.ModelSerializer):
    bijlagen = BijlageSerializer(many=True, required=False)

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "bijlagen",
            "aangemaakt_op",
        )
        read_only_fields = (
            "bijlagen",
            "aangemaakt_op",
        )


class TaakgebeurtenisStatusSerializer(WritableNestedModelSerializer):
    bijlagen = BijlageSerializer(many=True, required=False)
    taakstatus = TaakstatusSerializer(required=True)
    resolutie = serializers.CharField(required=False, allow_null=True)
    uitvoerder = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "bijlagen",
            "taakstatus",
            "resolutie",
            "omschrijving_intern",
            "gebruiker",
            "uitvoerder",
        )


class TaakopdrachtLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()
    applicatie = serializers.SerializerMethodField()
    melding = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:taakopdracht-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_applicatie(self, obj):
        return reverse(
            "v1:applicatie-detail",
            kwargs={"uuid": obj.applicatie.uuid},
            request=self.context.get("request"),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_melding(self, obj):
        return reverse(
            "v1:melding-detail",
            kwargs={"uuid": obj.melding.uuid},
            request=self.context.get("request"),
        )


class TaakopdrachtListSerializer(serializers.ModelSerializer):
    _links = TaakopdrachtLinksSerializer(source="*", read_only=True)
    status = TaakstatusSerializer(read_only=True)
    task_taak_aanmaken__status = serializers.SerializerMethodField()

    def get_task_taak_aanmaken__status(self, obj):
        return obj.task_taak_aanmaken.status if obj.task_taak_aanmaken else None

    class Meta:
        model = Taakopdracht
        fields = (
            "_links",
            "id",
            "uuid",
            "taaktype",
            "titel",
            "bericht",
            "verwijderd_op",
            "afgesloten_op",
            "status",
            "resolutie",
            "taak_url",
            "taak_aanmaken_error",
            "task_taak_aanmaken__status",
        )
        read_only_fields = (
            "_links",
            "id",
            "uuid",
            "taaktype",
            "titel",
            "bericht",
            "verwijderd_op",
            "afgesloten_op",
            "status",
            "resolutie",
            "taak_url",
            "taak_aanmaken_error",
            "task_taak_aanmaken__status",
        )


class TaakopdrachtSerializer(serializers.ModelSerializer):
    _links = TaakopdrachtLinksSerializer(source="*", read_only=True)
    taaktype = serializers.URLField()
    status = TaakstatusSerializer(read_only=True)
    taakgebeurtenissen_voor_taakopdracht = TaakgebeurtenisSerializer(
        many=True, read_only=True
    )
    gebruiker = serializers.CharField(required=False, allow_null=True)
    task_taak_aanmaken__status = serializers.SerializerMethodField()

    def get_task_taak_aanmaken__status(self, obj):
        return obj.task_taak_aanmaken.status if obj.task_taak_aanmaken else None

    class Meta:
        model = Taakopdracht
        fields = (
            "taaktype",
            "titel",
            "bericht",
            "additionele_informatie",
            "gebruiker",
            "_links",
            "id",
            "uuid",
            "verwijderd_op",
            "afgesloten_op",
            "status",
            "resolutie",
            "melding",
            "taakgebeurtenissen_voor_taakopdracht",
            "taak_url",
            "task_taak_aanmaken__status",
        )
        read_only_fields = (
            "_links",
            "id",
            "uuid",
            "verwijderd_op",
            "afgesloten_op",
            "status",
            "resolutie",
            "melding",
            "taakgebeurtenissen_voor_taakopdracht",
            "taak_url",
            "task_taak_aanmaken__status",
        )


class TaakopdrachtNotificatieTaakstatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taakstatus
        fields = ("naam",)


class TaakopdrachtNotificatieSerializer(serializers.ModelSerializer):
    bijlagen = BijlageSerializer(many=True, required=False, allow_null=True)
    taakstatus = TaakopdrachtNotificatieTaakstatusSerializer(required=True)
    resolutie = serializers.CharField(required=False, allow_null=True)
    resolutie_opgelost_herzien = serializers.BooleanField(
        required=False, allow_null=True
    )

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "bijlagen",
            "taakstatus",
            "resolutie",
            "omschrijving_intern",
            "gebruiker",
            "resolutie_opgelost_herzien",
        )


class TaakopdrachtNotificatieSaveSerializer(WritableNestedModelSerializer):
    bijlagen = BijlageSerializer(many=True, required=False, allow_null=True)
    taakstatus = TaakstatusSerializer(required=False, allow_null=True)
    resolutie = serializers.CharField(required=False, allow_null=True)
    aangemaakt_op = serializers.DateTimeField(required=False, allow_null=True)
    resolutie_opgelost_herzien = serializers.BooleanField(
        required=False, allow_null=True
    )

    def validate(self, data):
        from apps.taken.models import Taakstatus

        if not [data.values()]:
            raise serializers.ValidationError(
                "Er is minimaal 1 veld nodig voor de notificatie"
            )
        if data.get("taakstatus", {}).get("naam") in [
            Taakstatus.NaamOpties.VOLTOOID,
            Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
        ] and not data.get("resolutie"):
            raise serializers.ValidationError(
                "Als de taakopdracht wordt voltooid is een resolutie noodzakelijk"
            )

        return data

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "bijlagen",
            "taakstatus",
            "resolutie",
            "omschrijving_intern",
            "gebruiker",
            "resolutie_opgelost_herzien",
            "aangemaakt_op",
        )


class TaakopdrachtVerwijderenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taakgebeurtenis
        fields = []


class TaaktypeAantallenSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance


class TaakopdrachtHerstartTaskTaakAanmakenSerializer(serializers.Serializer):
    taakopdrachten = serializers.ListField(child=serializers.UUIDField())

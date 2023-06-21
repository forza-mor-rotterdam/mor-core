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
            "taakopdracht",
        )
        # read_only_fields = ("taakopdracht",)


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
            "bijlagen",
            "taakstatus",
            "omschrijving_intern",
            "taakopdracht",
            "gebruiker",
        )
        read_only_fields = (
            "_links",
            "aangemaakt_op",
            "bijlagen",
            "taakstatus",
            "omschrijving_intern",
            "taakopdracht",
        )


class TaakgebeurtenisStatusSerializer(WritableNestedModelSerializer):
    bijlagen = BijlageSerializer(many=True, required=False)
    taakstatus = TaakstatusSerializer(required=True)
    resolutie = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "bijlagen",
            "taakstatus",
            "resolutie",
            "omschrijving_intern",
            "gebruiker",
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


class TaakopdrachtSerializer(serializers.ModelSerializer):
    _links = TaakopdrachtLinksSerializer(source="*", read_only=True)
    taaktype = serializers.URLField()
    status = TaakstatusSerializer(read_only=True)
    taakgebeurtenissen_voor_taakopdracht = TaakgebeurtenisSerializer(
        many=True, read_only=True
    )
    gebruiker = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Taakopdracht
        fields = (
            "_links",
            "id",
            "uuid",
            "taaktype",
            "titel",
            "bericht",
            "additionele_informatie",
            "status",
            "melding",
            "taakgebeurtenissen_voor_taakopdracht",
            "gebruiker",
        )
        read_only_fields = (
            "_links",
            "id",
            "uuid",
            "status",
            "melding",
            "taakgebeurtenissen_voor_taakopdracht",
        )

from apps.aliassen.serializers import OnderwerpAliasSerializer
from apps.applicaties.models import Applicatie
from apps.bijlagen.serializers import BijlageAlleenLezenSerializer, BijlageSerializer
from apps.locatie.models import Adres, Graf, Lichtmast
from apps.locatie.serializers import (
    AdresSerializer,
    GrafSerializer,
    LichtmastSerializer,
    LocatieSerializer,
)
from apps.melders.serializers import MelderSerializer
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.services.pdok import PDOKService
from apps.signalen.models import Signaal
from apps.status.models import Status
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework import serializers
from rest_framework.reverse import reverse
from shapely.wkt import loads
from utils.exceptions import UrlFout


class SignaalLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()
    melding = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:signaal-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_melding(self, obj):
        return reverse(
            "v1:melding-detail",
            kwargs={"uuid": obj.melding.uuid},
            request=self.context.get("request"),
        )


class MeldingLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:melding-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )


class MeldinggebeurtenisSignaalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meldinggebeurtenis
        fields = ("omschrijving_extern",)
        read_only_fields = ("omschrijving_extern",)


class StatusSignaalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("naam",)
        read_only_fields = ("naam",)


class MeldingSignaalSerializer(serializers.ModelSerializer):
    _links = MeldingLinksSerializer(source="*", read_only=True)
    status = StatusSignaalSerializer(read_only=True)
    laatste_meldinggebeurtenis = serializers.SerializerMethodField()

    @extend_schema_field(MeldinggebeurtenisSignaalSerializer)
    def get_laatste_meldinggebeurtenis(self, obj):
        meldinggebeurtenis = (
            obj.meldinggebeurtenissen_voor_melding.all()
            .order_by("-aangemaakt_op")
            .first()
        )
        return MeldinggebeurtenisSignaalSerializer(meldinggebeurtenis).data

    class Meta:
        model = Melding
        fields = (
            "_links",
            "meta",
            "aangemaakt_op",
            "aangepast_op",
            "origineel_aangemaakt",
            "afgesloten_op",
            "status",
            "resolutie",
            "laatste_meldinggebeurtenis",
        )


class SignaalMeldingListSerializer(serializers.ModelSerializer):
    _links = SignaalLinksSerializer(source="*", read_only=True)
    bijlagen = BijlageAlleenLezenSerializer(many=True, read_only=True)  # OK

    class Meta:
        model = Signaal
        fields = (
            "_links",
            "bron_id",
            "bron_signaal_id",
            "aangemaakt_op",
            "bijlagen",
        )
        read_only_fields = (
            "_links",
            "bron_id",
            "bron_signaal_id",
            "aangemaakt_op",
        )


class SignaalListSerializer(WritableNestedModelSerializer):
    _links = SignaalLinksSerializer(source="*", read_only=True)
    melding = MeldingSignaalSerializer(required=False, read_only=True)
    melder = MelderSerializer(required=False)

    class Meta:
        model = Signaal
        fields = (
            "_links",
            "signaal_url",
            "bron_id",
            "bron_signaal_id",
            "melder",
            "melding",
        )
        read_only_fields = (
            "_links",
            "signaal_url",
            "bron_id",
            "bron_signaal_id",
            "melder",
            "melding",
        )


class SignaalAantallenSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wijken_gps_lookup = self.fetch_wijken_gps_lookup()

    def fetch_wijken_gps_lookup(self):
        gemeentecode = settings.WIJKEN_EN_BUURTEN_GEMEENTECODE
        wijken = PDOKService().get_wijken_middels_gemeentecode(gemeentecode)
        return {wijk.get("wijknaam"): wijk.get("centroide_ll") for wijk in wijken}

    def to_representation(self, instance):
        wijk = instance.get("wijk")
        gps = self.wijken_gps_lookup.get(wijk)
        gps = loads(gps)
        lat = str(gps.coords[0][1]) if gps else ""
        lon = str(gps.coords[0][0]) if gps else ""

        return {
            **instance,
            "lat": lat,
            "lon": lon,
        }


class SignaalSerializer(WritableNestedModelSerializer):
    _links = SignaalLinksSerializer(source="*", read_only=True)
    graven = GrafSerializer(many=True, required=False, write_only=True)
    adressen = AdresSerializer(many=True, required=False, write_only=True)
    lichtmasten = LichtmastSerializer(many=True, required=False, write_only=True)
    bijlagen = BijlageSerializer(many=True, required=False)
    onderwerpen = OnderwerpAliasSerializer(many=True, required=False)
    melder = MelderSerializer(required=False)
    locaties_voor_signaal = LocatieSerializer(many=True, read_only=True)

    def validate_signaal_url(self, data):
        applicatie = Applicatie.vind_applicatie_obv_uri(data)
        if not applicatie:
            raise UrlFout("signaal_url")
        return data

    def create(self, validated_data):
        locaties = (("adressen", Adres), ("lichtmasten", Lichtmast), ("graven", Graf))
        locaties_data = {
            loc[0]: validated_data.pop(loc[0], None)
            for loc in locaties
            if validated_data.get(loc[0])
        }
        for loc in locaties:
            validated_data.pop(loc[0], None)
        signaal = super().create(validated_data)

        for location in locaties:
            model = location[1]
            for loc in locaties_data.get(location[0], []):
                model.objects.create(**loc, signaal=signaal)
            validated_data.pop(location[0], None)

        return signaal

    class Meta:
        model = Signaal
        fields = (
            "_links",
            "uuid",
            "signaal_url",
            "signaal_data",
            "bron_id",
            "bron_signaal_id",
            "origineel_aangemaakt",
            "urgentie",
            "omschrijving_melder",
            "aanvullende_informatie",
            "aanvullende_vragen",
            "meta",
            "meta_uitgebreid",
            "onderwerpen",
            "bijlagen",
            "melder",
            "adressen",
            "lichtmasten",
            "graven",
            "aangemaakt_op",
            "melding",
            "locaties_voor_signaal",
        )
        read_only_fields = (
            "signaal_data",
            "aangemaakt_op",
            "adressen",
            "lichtmasten",
            "graven",
            "locaties_voor_signaal",
        )

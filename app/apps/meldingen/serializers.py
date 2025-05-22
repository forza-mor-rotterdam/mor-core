from apps.aliassen.serializers import OnderwerpAliasSerializer
from apps.bijlagen.models import Bijlage
from apps.bijlagen.serializers import BijlageAlleenLezenSerializer, BijlageSerializer
from apps.locatie.models import Adres, Graf, Lichtmast
from apps.locatie.serializers import (
    AdresSerializer,
    GrafSerializer,
    LichtmastSerializer,
    LocatieRelatedField,
)
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.signalen.serializers import SignaalMeldingListSerializer, SignaalSerializer
from apps.status.serializers import StatusSerializer
from apps.taken.models import Taakgebeurtenis, Taakopdracht, Taakstatus
from apps.taken.serializers import (
    TaakgebeurtenisBijlagenSerializer,
    TaakgebeurtenisSerializer,
    TaakopdrachtSerializer,
)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework import serializers
from rest_framework.reverse import reverse


class MeldingLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:melding-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )


class MeldingGebeurtenisLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:meldinggebeurtenis-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )


class MeldingGebeurtenisStatusSerializer(WritableNestedModelSerializer):
    bijlagen = BijlageSerializer(many=True, required=False)
    status = StatusSerializer(required=True)
    gebeurtenis_type = serializers.CharField(required=False)
    resolutie = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Meldinggebeurtenis
        fields = (
            "aangemaakt_op",
            "gebeurtenis_type",
            "bijlagen",
            "status",
            "resolutie",
            "omschrijving_intern",
            "omschrijving_extern",
            "melding",
            "gebruiker",
        )
        read_only_fields = ("aangemaakt_op",)


class MeldingGebeurtenisUrgentieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meldinggebeurtenis
        fields = (
            "urgentie",
            "omschrijving_intern",
            "gebeurtenis_type",
            "melding",
            "gebruiker",
        )


class MeldinggebeurtenisSerializer(WritableNestedModelSerializer):
    _links = MeldingGebeurtenisLinksSerializer(source="*", read_only=True)
    bijlagen = BijlageSerializer(many=True, required=False)
    status = StatusSerializer(required=False)
    taakgebeurtenis = TaakgebeurtenisSerializer(required=False)
    locatie = AdresSerializer(required=False)

    class Meta:
        model = Meldinggebeurtenis
        fields = (
            "_links",
            "aangemaakt_op",
            "gebeurtenis_type",
            "bijlagen",
            "status",
            "omschrijving_intern",
            "omschrijving_extern",
            "melding",
            "taakgebeurtenis",
            "gebruiker",
            "locatie",
            "urgentie",
        )
        read_only_fields = (
            "_links",
            "aangemaakt_op",
            "gebeurtenis_type",
            "status",
            "melding",
            "taakgebeurtenis",
            "locatie",
            "urgentie",
        )
        validators = []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class MeldingAanmakenSerializer(WritableNestedModelSerializer):
    graven = GrafSerializer(many=True, required=False)
    adressen = AdresSerializer(many=True, required=False)
    lichtmasten = LichtmastSerializer(many=True, required=False)
    bijlagen = BijlageSerializer(many=True, required=False)
    onderwerpen = OnderwerpAliasSerializer(many=True, required=False)

    class Meta:
        model = Melding
        fields = (
            "origineel_aangemaakt",
            "meta",
            "meta_uitgebreid",
            "onderwerpen",
            "bijlagen",
            "graven",
            "adressen",
            "lichtmasten",
        )

    def create(self, validated_data):
        locaties = (("adressen", Adres), ("lichtmasten", Lichtmast), ("graven", Graf))
        locaties_data = {
            loc[0]: validated_data.pop(loc[0], None)
            for loc in locaties
            if validated_data.get(loc[0])
        }
        melding = super().create(validated_data)

        for location in locaties:
            model = location[1]
            for loc in locaties_data.get(location[0], []):
                model.objects.create(**loc, melding=melding)
            validated_data.pop(location[0], None)

        return melding


class OnderwerpBronUrlField(serializers.RelatedField):
    def to_representation(self, value):
        return value.bron_url


class MeldinggebeurtenisMeldingLijstSerializer(serializers.ModelSerializer):
    bijlagen = BijlageAlleenLezenSerializer(many=True, read_only=True)
    taakgebeurtenis = TaakgebeurtenisBijlagenSerializer(required=False)

    class Meta:
        model = Meldinggebeurtenis
        fields = (
            "omschrijving_extern",
            "taakgebeurtenis",
            "bijlagen",
            "aangemaakt_op",
        )
        read_only_fields = ("omschrijving_extern",)


class TaakopdrachtStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taakstatus
        fields = ("naam",)


class TaakgebeurtenisMeldingLijstSerializer(TaakgebeurtenisSerializer):
    bijlagen = BijlageAlleenLezenSerializer(many=True, read_only=True)

    class Meta:
        model = Taakgebeurtenis
        fields = (
            "bijlagen",
            "resolutie",
        )


class TaakopdrachtMeldingLijstSerializer(serializers.ModelSerializer):
    status = TaakopdrachtStatusSerializer(read_only=True)

    class Meta:
        model = Taakopdracht
        fields = (
            "titel",
            "resolutie",
            "verwijderd_op",
            "afgesloten_op",
            "status",
        )


class BijlageRecentSerializer(BijlageSerializer):
    class Meta:
        model = Bijlage
        fields = (
            "afbeelding",
            "afbeelding_verkleind",
            "is_afbeelding",
            "afbeelding_relative_url",
            "afbeelding_verkleind_relative_url",
        )
        read_only_fields = (
            "afbeelding",
            "afbeelding_verkleind",
            "is_afbeelding",
            "afbeelding_relative_url",
            "afbeelding_verkleind_relative_url",
        )

    def to_representation(self, instance):
        representation = super().to_representation(
            instance.order_by("-aangemaakt_op").first()
        )
        return representation


class MeldingSerializer(serializers.ModelSerializer):
    _links = MeldingLinksSerializer(source="*", read_only=True)
    status = StatusSerializer(read_only=True)
    onderwerpen = OnderwerpBronUrlField(many=True, read_only=True)
    signalen_voor_melding = SignaalMeldingListSerializer(many=True, read_only=True)
    taakopdrachten_voor_melding = TaakopdrachtMeldingLijstSerializer(
        many=True, read_only=True
    )
    referentie_locatie = LocatieRelatedField(read_only=True)
    thumbnail_afbeelding = BijlageAlleenLezenSerializer(read_only=True)

    class Meta:
        model = Melding
        fields = (
            "_links",
            "id",
            "uuid",
            "aangemaakt_op",
            "aangepast_op",
            "origineel_aangemaakt",
            "afgesloten_op",
            "urgentie",
            "thumbnail_afbeelding",
            "meta",
            "onderwerpen",
            "referentie_locatie",
            "signalen_voor_melding",
            "status",
            "resolutie",
            "taakopdrachten_voor_melding",
        )
        read_only_fields = (
            "id",
            "uuid",
            "aangemaakt_op",
            "aangepast_op",
            "urgentie",
            "thumbnail_afbeelding",
            "origineel_aangemaakt",
            "omschrijving_kort",
            "afgesloten_op",
            "meta",
            "meta_uitgebreid",
            "resolutie",
        )


class MeldingDetailSerializer(MeldingSerializer):
    _links = MeldingLinksSerializer(source="*", read_only=True)
    locaties_voor_melding = LocatieRelatedField(many=True, read_only=True)
    bijlagen = BijlageSerializer(many=True, required=False)
    status = StatusSerializer()
    meldinggebeurtenissen = MeldinggebeurtenisSerializer(
        source="meldinggebeurtenissen_voor_melding", many=True, read_only=True
    )
    taakopdrachten_voor_melding = TaakopdrachtSerializer(many=True, read_only=True)
    signalen_voor_melding = SignaalSerializer(many=True, read_only=True)
    onderwerpen = OnderwerpBronUrlField(many=True, read_only=True)

    class Meta:
        model = Melding
        fields = (
            "_links",
            "id",
            "uuid",
            "aangemaakt_op",
            "aangepast_op",
            "origineel_aangemaakt",
            "afgesloten_op",
            "urgentie",
            "meta",
            "meta_uitgebreid",
            "onderwerpen",
            "bijlagen",
            "locaties_voor_melding",
            "status",
            "resolutie",
            "meldinggebeurtenissen",
            "taakopdrachten_voor_melding",
            "signalen_voor_melding",
        )
        read_only_fields = (
            "_links",
            "id",
            "uuid",
            "aangemaakt_op",
            "aangepast_op",
            "urgentie",
            "origineel_aangemaakt",
            "afgesloten_op",
            "meta",
            "meta_uitgebreid",
            "onderwerpen",
            "bijlagen",
            "locaties_voor_melding",
            "status",
            "resolutie",
            "volgende_statussen",
            "meldinggebeurtenissen",
            "taakopdrachten_voor_melding",
            "signalen_voor_melding",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Sorteer locaties_voor_melding op 'gewicht' veld
        locaties_sorted = sorted(
            representation["locaties_voor_melding"],
            key=lambda locatie: locatie.get("gewicht", 0),
            reverse=True,
        )

        # Vervang originele locaties_voor_melding met de gesorteerde lijst
        representation["locaties_voor_melding"] = locaties_sorted

        return representation


class MeldingAantallenSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    wijk = serializers.CharField()
    onderwerp = serializers.CharField(source="onderwerp_naam")

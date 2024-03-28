from apps.aliassen.serializers import OnderwerpAliasSerializer
from apps.bijlagen.models import Bijlage
from apps.bijlagen.serializers import BijlageSerializer
from apps.locatie.models import Adres, Graf, Lichtmast
from apps.locatie.serializers import (
    AdresSerializer,
    GrafSerializer,
    LichtmastSerializer,
    LocatieRelatedField,
)
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.signalen.models import Signaal
from apps.signalen.serializers import SignaalMeldingListSerializer, SignaalSerializer
from apps.status.serializers import StatusSerializer
from apps.taken.models import Taakgebeurtenis
from apps.taken.serializers import TaakgebeurtenisSerializer, TaakopdrachtSerializer
from config.context import db
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
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


class MeldingSerializer(serializers.ModelSerializer):
    _links = MeldingLinksSerializer(source="*", read_only=True)
    locaties_voor_melding = LocatieRelatedField(many=True, read_only=True)
    status = StatusSerializer(read_only=True)
    bijlage = serializers.SerializerMethodField()
    aantal_actieve_taken = serializers.SerializerMethodField()
    laatste_meldinggebeurtenis = serializers.SerializerMethodField()
    onderwerpen = OnderwerpBronUrlField(many=True, read_only=True)
    signalen_voor_melding = SignaalMeldingListSerializer(many=True, read_only=True)

    @extend_schema_field(BijlageSerializer)
    def get_bijlage(self, obj):
        with db(settings.READONLY_DATABASE_KEY):
            taakgebeurtenissen_voor_melding = Taakgebeurtenis.objects.all().filter(
                taakopdracht__in=obj.taakopdrachten_voor_melding.all()
            )
            return BijlageSerializer(
                Bijlage.objects.filter(
                    Q(
                        object_id__in=obj.meldinggebeurtenissen_voor_melding.all().values_list(
                            "id", flat=True
                        ),
                        content_type=ContentType.objects.get_for_model(
                            Meldinggebeurtenis
                        ),
                    )
                    | Q(
                        object_id__in=taakgebeurtenissen_voor_melding.values_list(
                            "id", flat=True
                        ),
                        content_type=ContentType.objects.get_for_model(Taakgebeurtenis),
                    )
                    | Q(
                        object_id__in=obj.signalen_voor_melding.all().values_list(
                            "id", flat=True
                        ),
                        content_type=ContentType.objects.get_for_model(Signaal),
                    )
                    | Q(
                        object_id=obj.id,
                        content_type=ContentType.objects.get_for_model(Melding),
                    )
                )
                .order_by("aangemaakt_op")
                .first()
            ).data

    @extend_schema_field(OpenApiTypes.INT)
    def get_aantal_actieve_taken(self, obj):
        with db(settings.READONLY_DATABASE_KEY):
            return obj.taakopdrachten_voor_melding.exclude(
                status__naam="voltooid"
            ).count()

    def get_laatste_meldinggebeurtenis(self, obj):
        with db(settings.READONLY_DATABASE_KEY):
            meldinggebeurtenis = (
                obj.meldinggebeurtenissen_voor_melding.all()
                .order_by("-aangemaakt_op")
                .first()
            )
            return MeldinggebeurtenisSerializer(meldinggebeurtenis).data

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
            "onderwerpen",
            "bijlage",
            "locaties_voor_melding",
            "signalen_voor_melding",
            "status",
            "resolutie",
            "aantal_actieve_taken",
            "laatste_meldinggebeurtenis",
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
            "bijlage",
            "locaties_voor_melding",
            "status",
            "resolutie",
            "signalen_voor_melding",
            "laatste_meldinggebeurtenis",
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


class MeldingDetailSerializer(MeldingSerializer):
    _links = MeldingLinksSerializer(source="*", read_only=True)
    locaties_voor_melding = LocatieRelatedField(many=True, read_only=True)
    bijlagen = BijlageSerializer(many=True, required=False)
    status = StatusSerializer()
    volgende_statussen = serializers.ListField(
        source="status.volgende_statussen",
        child=serializers.CharField(),
        read_only=True,
    )
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
            "volgende_statussen",
            "meldinggebeurtenissen",
            "taakopdrachten_voor_melding",
            "signalen_voor_melding",
            "laatste_meldinggebeurtenis",
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
            "laatste_meldinggebeurtenis",
        )

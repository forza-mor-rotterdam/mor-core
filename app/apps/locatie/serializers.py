from apps.locatie.models import Adres, Geometrie, Graf, Lichtmast, Locatie
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField


class AdresBasisSerializer(serializers.Serializer):
    plaatsnaam = serializers.CharField(max_length=255, required=False, allow_blank=True)
    straatnaam = serializers.CharField(max_length=255, required=False, allow_blank=True)
    huisnummer = serializers.IntegerField(required=False)
    huisletter = serializers.CharField(max_length=1, required=False, allow_blank=True)
    toevoeging = serializers.CharField(max_length=4, required=False, allow_blank=True)
    postcode = serializers.CharField(max_length=7, required=False, allow_blank=True)
    wijknaam = serializers.CharField(max_length=255, required=False, allow_blank=True)
    buurtnaam = serializers.CharField(max_length=255, required=False, allow_blank=True)
    geometrie = GeometryField(required=False)


class GrafBasisSerializer(serializers.Serializer):
    plaatsnaam = serializers.CharField(max_length=255)
    begraafplaats = serializers.CharField(max_length=50)
    grafnummer = serializers.CharField(max_length=10, required=False, allow_blank=True)
    vak = serializers.CharField(max_length=10, required=False, allow_blank=True)
    geometrie = GeometryField(required=False)


class LichtmastBasisSerializer(serializers.Serializer):
    lichtmast_id = serializers.CharField(max_length=255)
    geometrie = GeometryField(required=False)

    class Meta:
        model = Lichtmast
        fields = (
            "lichtmast_id",
            "geometrie",
        )


class GeometrieBasisSerializer(serializers.Serializer):
    geometrie = GeometryField(required=False)


class GeometrieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geometrie
        fields = (
            "bron",
            "geometrie",
        )


class LocatieSerializer(WritableNestedModelSerializer):
    class Meta:
        model = Locatie
        fields = "__all__"


class LocatieRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        serializer = LocatieSerializer(value)
        return serializer.data


class AdresSerializer(AdresBasisSerializer, serializers.ModelSerializer):
    class Meta:
        model = Adres
        fields = (
            "plaatsnaam",
            "straatnaam",
            "huisnummer",
            "huisletter",
            "toevoeging",
            "postcode",
            "wijknaam",
            "buurtnaam",
            "geometrie",
            "gebruiker",
            "gewicht",
        )


class GrafSerializer(GrafBasisSerializer, serializers.ModelSerializer):
    class Meta:
        model = Graf
        fields = (
            "plaatsnaam",
            "begraafplaats",
            "grafnummer",
            "vak",
            "geometrie",
        )


class LichtmastSerializer(LichtmastBasisSerializer, serializers.ModelSerializer):
    class Meta:
        model = Lichtmast
        fields = (
            "lichtmast_id",
            "geometrie",
        )


class BuurtWijkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Locatie
        fields = (
            "buurtnaam",
            "wijknaam",
            "plaatsnaam",
        )

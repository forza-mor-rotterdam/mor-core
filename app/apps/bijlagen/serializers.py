import filetype
from apps.bijlagen.models import Bijlage
from drf_extra_fields.fields import Base64FileField
from rest_framework import serializers


class DefaultBase64File(Base64FileField):
    ALLOWED_TYPES = ["jpg", "jpeg", "png", "rtf", "doc", "docx", "heic"]

    def get_file_extension(self, filename, decoded_file):
        # TODO nadenken over beter upload van bestanden, vooral grote bestanden komen niet heel door
        kind = filetype.guess(decoded_file)
        return kind.extension


class BijlageSerializer(serializers.ModelSerializer):
    """
    Bijlage comment van serializer
    """

    bestand = DefaultBase64File()
    afbeelding_relative_url = serializers.SerializerMethodField()
    afbeelding_verkleind_relative_url = serializers.SerializerMethodField()

    def get_afbeelding_relative_url(self, obj):
        return obj.afbeelding.url if obj.afbeelding else None

    def get_afbeelding_verkleind_relative_url(self, obj):
        return obj.afbeelding_verkleind.url if obj.afbeelding_verkleind else None

    class Meta:
        model = Bijlage
        fields = (
            "uuid",
            "bestand",
            "afbeelding",
            "afbeelding_verkleind",
            "mimetype",
            "is_afbeelding",
            "afbeelding_relative_url",
            "afbeelding_verkleind_relative_url",
        )
        read_only_fields = (
            "uuid",
            "afbeelding",
            "afbeelding_verkleind",
            "is_afbeelding",
            "mimetype",
            "afbeelding_relative_url",
            "afbeelding_verkleind_relative_url",
        )


class BijlageAlleenLezenSerializer(serializers.ModelSerializer):
    """
    Alleen lezen Bijlage serializer
    """

    afbeelding_relative_url = serializers.SerializerMethodField()
    afbeelding_verkleind_relative_url = serializers.SerializerMethodField()

    def get_afbeelding_relative_url(self, obj):
        return obj.afbeelding.url if obj.afbeelding else None

    def get_afbeelding_verkleind_relative_url(self, obj):
        return obj.afbeelding_verkleind.url if obj.afbeelding_verkleind else None

    class Meta:
        model = Bijlage
        fields = (
            "aangemaakt_op",
            "afbeelding",
            "afbeelding_verkleind",
            "afbeelding_relative_url",
            "afbeelding_verkleind_relative_url",
        )
        read_only_fields = (
            "aangemaakt_op",
            "afbeelding",
            "afbeelding_verkleind",
            "afbeelding_relative_url",
            "afbeelding_verkleind_relative_url",
        )

from apps.aliassen.models import OnderwerpAlias
from apps.instellingen.models import Instelling
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utils.exceptions import UrlFout


class OnderwerpAliasLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return obj.bron_url


class OnderwerpAliasListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnderwerpAlias
        fields = (
            "pk",
            "bron_url",
        )
        read_only_fields = (
            "pk",
            "bron_url",
        )


class OnderwerpAliasSerializer(serializers.ModelSerializer):
    _links = OnderwerpAliasLinksSerializer(source="*", read_only=True)
    naam = serializers.SerializerMethodField()

    def get_naam(self, obj):
        return obj.response_json.get(
            "naam", obj.response_json.get("name", obj.bron_url)
        )

    """
    OnderwerpAlias van een Melding of Signaal
    """

    def validate_bron_url(self, data):
        is_onderwerp_bron_url_valide = Instelling.actieve_instelling().valideer_url(
            "onderwerpen_basis_url", data
        )
        if not is_onderwerp_bron_url_valide:
            raise UrlFout("onderwerp bron_url")
        return data

    def create(self, validated_data):
        onderwerpalias, aangemaakt = OnderwerpAlias.objects.get_or_create(
            **validated_data
        )
        return onderwerpalias

    class Meta:
        model = OnderwerpAlias
        fields = (
            "_links",
            "naam",
            "bron_url",
        )
        read_only_fields = (
            "_links",
            "naam",
        )

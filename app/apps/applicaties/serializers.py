from apps.applicaties.models import Applicatie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.reverse import reverse


class TaakapplicatieLinksSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, obj):
        return reverse(
            "v1:applicatie-detail",
            kwargs={"uuid": obj.uuid},
            request=self.context.get("request"),
        )


class TaakapplicatieSerializer(serializers.ModelSerializer):
    _links = TaakapplicatieLinksSerializer(source="*", read_only=True)

    class Meta:
        model = Applicatie
        fields = (
            "_links",
            "uuid",
            "naam",
            "basis_url",
            "applicatie_type",
        )
        read_only_fields = (
            "_links",
            "uuid",
            "naam",
            "basis_url",
            "applicatie_type",
        )

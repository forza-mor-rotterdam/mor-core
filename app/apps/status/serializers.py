from apps.status.models import Status
from django.core.exceptions import ValidationError
from rest_framework import serializers


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = (
            "naam",
            "melding",
        )

    def validate(self, attrs):
        melding = attrs.get("melding")
        nieuwe_status_naam = attrs.get("naam")
        if (
            nieuwe_status_naam
            and melding.status
            and not melding.status.status_verandering_toegestaan(nieuwe_status_naam)
        ):
            raise ValidationError(
                f"Vorige status: {melding.status.naam} -> Nieuwe status: {nieuwe_status_naam}"
            )
        return attrs


class StatusVeranderingSerializer(serializers.Serializer):
    class Meta:
        fields = (
            "wijk",
            "onderwerp",
            "begin_status",
            "eind_status",
            "duur_seconden_gemiddeld",
            "aantal",
        )

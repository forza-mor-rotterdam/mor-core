from apps.melders.models import Melder
from rest_framework import serializers


class MelderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Melder
        fields = (
            "naam",
            "voornaam",
            "achternaam",
            "email",
            "telefoonnummer",
        )

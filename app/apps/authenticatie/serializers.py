from rest_framework import serializers


class GebruikerSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(
        required=False, allow_blank=True, max_length=150, allow_null=True
    )
    last_name = serializers.CharField(
        required=False, allow_blank=True, max_length=150, allow_null=True
    )
    telefoonnummer = serializers.CharField(
        required=False, allow_blank=True, max_length=17, allow_null=True
    )

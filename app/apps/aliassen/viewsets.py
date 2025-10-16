from apps.aliassen.models import OnderwerpAlias
from apps.aliassen.serializers import OnderwerpAliasListSerializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets


@extend_schema(
    parameters=[
        OpenApiParameter("signaal_url", OpenApiTypes.URI, OpenApiParameter.QUERY),
    ]
)
class OnderwerpAliasViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = OnderwerpAlias.objects.all()
    serializer_class = OnderwerpAliasListSerializer

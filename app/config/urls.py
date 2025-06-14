from apps.aliassen.viewsets import OnderwerpAliasViewSet
from apps.applicaties.viewsets import TaakapplicatieViewSet
from apps.authenticatie.views import (
    GetGebruikerAPIView,
    LoginView,
    LogoutView,
    SetGebruikerAPIView,
)
from apps.bijlagen.viewsets import BijlageViewSet
from apps.health.views import healthz
from apps.locatie.viewsets import LocatieViewSet
from apps.meldingen.views import prometheus_django_metrics, root, serve_protected_media
from apps.meldingen.viewsets import (
    MeldinggebeurtenisViewSet,
    MeldingViewSet,
    SpecificatieViewSet,
)
from apps.signalen.viewsets import SignaalViewSet
from apps.status.viewsets import StatusViewSet
from apps.taken.viewsets import TaakgebeurtenisViewSet, TaakopdrachtViewSet
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django_db_schema_renderer.urls import schema_urls
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"signaal", SignaalViewSet, basename="signaal")
router.register(r"melding", MeldingViewSet, basename="melding")
router.register(
    r"meldinggebeurtenis", MeldinggebeurtenisViewSet, basename="meldinggebeurtenis"
)
router.register(r"onderwerp-alias", OnderwerpAliasViewSet, basename="onderwerp-alias")
router.register(r"applicatie", TaakapplicatieViewSet, basename="applicatie")
router.register(r"taakapplicatie", TaakapplicatieViewSet, basename="taakapplicatie")
router.register(r"taakopdracht", TaakopdrachtViewSet, basename="taakopdracht")
router.register(r"taakgebeurtenis", TaakgebeurtenisViewSet, basename="taakgebeurtenis")
router.register(r"bijlage", BijlageViewSet, basename="bijlage")
router.register(r"status", StatusViewSet, basename="status")
router.register(r"locatie", LocatieViewSet, basename="locatie")
router.register(r"specificatie", SpecificatieViewSet, basename="specificatie")

urlpatterns = [
    path("", root, name="root"),
    path("api/v1/", include((router.urls, "app"), namespace="v1")),
    path(
        "api/v1/gebruiker/<str:email>/",
        GetGebruikerAPIView.as_view(),
        name="get_gebruiker",
    ),
    path("api/v1/gebruiker/", SetGebruikerAPIView.as_view(), name="set_gebruiker"),
    path("api-token-auth/", views.obtain_auth_token),
    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path("health/", include("health_check.urls")),
    path("healthz/", healthz, name="healthz"),
    path("db-schema/", include((schema_urls, "db-schema"))),
    path("plate/", include("django_spaghetti.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    re_path(r"^media", serve_protected_media, name="protected_media"),
    path("metrics", prometheus_django_metrics, name="prometheus_django_metrics"),
]

if not settings.ENABLE_DJANGO_ADMIN_LOGIN:
    urlpatterns += [
        path(
            "admin/login/",
            RedirectView.as_view(url="/login/?next=/admin/"),
            name="admin_login",
        ),
        path(
            "admin/logout/",
            RedirectView.as_view(url="/logout/?next=/"),
            name="admin_logout",
        ),
    ]

if settings.OIDC_ENABLED:
    urlpatterns += [
        path("oidc/", include("mozilla_django_oidc.urls")),
    ]

urlpatterns += [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += debug_toolbar_urls()

import locale
import logging
import os
import sys
from os.path import join

import requests
import urllib3

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUE_VALUES = [True, "True", "true", "1"]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", os.environ.get("DJANGO_SECRET_KEY"))
FERNET_KEY = os.getenv(
    "FERNET_KEY", "Fp9p5Ml9hK2BravAUDd4O4pn9_KcBTfFbh-QEuuBN0E="
).encode()


GIT_SHA = os.getenv("GIT_SHA")
DEPLOY_DATE = os.getenv("DEPLOY_DATE", "")
ENVIRONMENT = os.getenv("ENVIRONMENT")
DEBUG = ENVIRONMENT == "development"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

USE_TZ = True
TIME_ZONE = "Europe/Amsterdam"
USE_L10N = True
USE_I18N = False
LANGUAGE_CODE = "nl-NL"
LANGUAGES = [("nl", "Dutch")]

PROTOCOL = "https" if not DEBUG else "http"
PORT = "" if not DEBUG else ":8002"

DEFAULT_ALLOWED_HOSTS = ".forzamor.nl,localhost,127.0.0.1,.mor.local"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",")

ENABLE_DJANGO_ADMIN_LOGIN = os.getenv("ENABLE_DJANGO_ADMIN_LOGIN", False) in TRUE_VALUES

LOGIN_URL = "login"
LOGOUT_URL = "logout"

SIGNALEN_API = os.getenv("SIGNALEN_API")
MELDING_API = os.getenv("MELDING_API")

MELDING_VERANDERD_NOTIFICATIE_URL = os.getenv(
    "MELDING_VERANDERD_NOTIFICATIE_URL", "/api/v1/melding/"
)

ALLOW_UNAUTHORIZED_MEDIA_ACCESS = (
    os.getenv("ALLOW_UNAUTHORIZED_MEDIA_ACCESS", False) in TRUE_VALUES
)
TOKEN_API_RELATIVE_URL = os.getenv("TOKEN_API_RELATIVE_URL", "/api-token-auth/")
MELDINGEN_TOKEN_TIMEOUT = 60 * 60

INSTALLED_APPS = (
    # templates override
    "apps.health",
    "django_db_schema_renderer",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.gis",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_gis",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "django_extensions",
    "django_spaghetti",
    "health_check",
    "health_check.cache",
    "health_check.storage",
    "health_check.db",
    "health_check.contrib.migrations",
    "health_check.contrib.celery_ping",
    "sorl.thumbnail",
    "debug_toolbar",
    "django_prometheus",
    "django_rename_app",
    "django_celery_beat",
    "django_celery_results",
    # Apps
    "apps.authenticatie",
    "apps.bijlagen",
    "apps.melders",
    "apps.notificaties",
    "apps.aliassen",
    "apps.applicaties",
    "apps.meldingen",
    "apps.taken",
    "apps.status",
    "apps.signalen",
    "apps.locatie",
    "apps.classificatie",
    "apps.instellingen",
)

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

# django-permissions-policy settings
PERMISSIONS_POLICY = {
    "accelerometer": [],
    "ambient-light-sensor": [],
    "autoplay": [],
    "camera": [],
    "display-capture": [],
    "document-domain": [],
    "encrypted-media": [],
    "fullscreen": [],
    "geolocation": [],
    "gyroscope": [],
    "interest-cohort": [],
    "magnetometer": [],
    "microphone": [],
    "midi": [],
    "payment": [],
    "usb": [],
}


STATIC_URL = "/static/"
STATIC_ROOT = os.path.normpath(join(os.path.dirname(BASE_DIR), "static"))

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.normpath(join(os.path.dirname(BASE_DIR), "media"))

if DEBUG:
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + [
        "127.0.0.1",
        "10.0.2.2",
    ]

# Database settings
DEFAULT_DATABASE_KEY = "default"
READONLY_DATABASE_KEY = "readonly"

DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST_OVERRIDE")
DATABASE_PORT = os.getenv("DATABASE_PORT_OVERRIDE")

READONLY_DATABASE_NAME = os.getenv("READONLY_DATABASE_NAME", DATABASE_NAME)
READONLY_DATABASE_USER = os.getenv("READONLY_DATABASE_USER", DATABASE_USER)
READONLY_DATABASE_PASSWORD = os.getenv("READONLY_DATABASE_PASSWORD", DATABASE_PASSWORD)
READONLY_DATABASE_HOST = os.getenv("READONLY_DATABASE_HOST", DATABASE_HOST)
READONLY_DATABASE_PORT = os.getenv("READONLY_DATABASE_PORT", DATABASE_PORT)

DEFAULT_DATABASE = {
    "ENGINE": "django.contrib.gis.db.backends.postgis",
    "NAME": DATABASE_NAME,  # noqa:
    "USER": DATABASE_USER,  # noqa
    "PASSWORD": DATABASE_PASSWORD,  # noqa
    "HOST": DATABASE_HOST,  # noqa
    "PORT": DATABASE_PORT,  # noqa
}
READONLY_DATABASE = {
    "ENGINE": "django.contrib.gis.db.backends.postgis",
    "NAME": READONLY_DATABASE_NAME,  # noqa:
    "USER": READONLY_DATABASE_USER,  # noqa
    "PASSWORD": READONLY_DATABASE_PASSWORD,  # noqa
    "HOST": READONLY_DATABASE_HOST,  # noqa
    "PORT": READONLY_DATABASE_PORT,  # noqa
}

DATABASES = {
    DEFAULT_DATABASE_KEY: DEFAULT_DATABASE,
    READONLY_DATABASE_KEY: READONLY_DATABASE,
}
DATABASES.update(
    {
        "alternate": DEFAULT_DATABASE,
    }
    if ENVIRONMENT in ["unittest", "development"]
    else {}
)
DATABASE_ROUTERS = ["config.routers.DatabaseRouter"]


CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

CELERY_BROKER_URL = "redis://redis:6379/0"
BROKER_URL = CELERY_BROKER_URL

CELERY_RESULT_BACKEND = "django-db"
CELERY_RESULT_EXTENDED = True

CELERY_WORKER_CONCURRENCY = 2
CELERY_WORKER_MAX_TASKS_PER_CHILD = 20
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000

if ENVIRONMENT in ["unittest", "development"]:
    DJANGO_TEST_USERNAME = os.getenv("DJANGO_TEST_USERNAME", "test")
    DJANGO_TEST_EMAIL = os.getenv("DJANGO_TEST_EMAIL", "test@test.com")
    DJANGO_TEST_PASSWORD = os.getenv("DJANGO_TEST_PASSWORD", "insecure")

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
AUTH_USER_MODEL = "authenticatie.Gebruiker"

SITE_ID = 1
SITE_NAME = os.getenv("SITE_NAME", "MOR CORE")
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "localhost")

# Django REST framework settings
REST_FRAMEWORK = dict(
    PAGE_SIZE=5,
    UNAUTHENTICATED_USER={},
    UNAUTHENTICATED_TOKEN={},
    DEFAULT_PAGINATION_CLASS="utils.pagination.LimitOffsetPagination",
    DEFAULT_FILTER_BACKENDS=("django_filters.rest_framework.DjangoFilterBackend",),
    DEFAULT_THROTTLE_RATES={
        "nouser": os.getenv("PUBLIC_THROTTLE_RATE", "60/hour"),
    },
    DEFAULT_PARSER_CLASSES=[
        "rest_framework.parsers.JSONParser",
        "utils.parsers.NestedMultipartParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    DEFAULT_SCHEMA_CLASS="drf_spectacular.openapi.AutoSchema",
    DEFAULT_PERMISSION_CLASSES=("rest_framework.permissions.IsAuthenticated",),
    DEFAULT_AUTHENTICATION_CLASSES=("apps.authenticatie.auth.TokenAuthentication",),
    EXCEPTION_HANDLER="utils.exception_handlers.api_exception_handler",
)

handler500 = "rest_framework.exceptions.server_error"
handler400 = "rest_framework.exceptions.bad_request"

SPECTACULAR_SETTINGS = {
    "TITLE": "MOR CORE",
    "DESCRIPTION": "Voor het organiseren en beheren van Meldingen Openbare Ruimte",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

TAAKTYPE_APPLICATIE_URL = os.getenv(
    "TAAKTYPE_APPLICATIE_URL", "https://taakr.forzamor.nl"
)

# Django security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
CORS_ORIGIN_WHITELIST = ()
CORS_ORIGIN_ALLOW_ALL = False
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_NAME = "__Host-sessionid" if not DEBUG else "sessionid"
CSRF_COOKIE_NAME = "__Host-csrftoken" if not DEBUG else "csrftoken"
SESSION_COOKIE_SAMESITE = "Lax"  # Strict does not work well together with OIDC
CSRF_COOKIE_SAMESITE = "Lax"  # Strict does not work well together with OIDC

# Settings for Content-Security-Policy header
CSP_DEFAULT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "blob:",
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
    "cdn.redoc.ly",
    "cdn.jsdelivr.net",
    "map1c.vis.earthdata.nasa.gov",
    "map1b.vis.earthdata.nasa.gov",
    "map1a.vis.earthdata.nasa.gov",
)
CSP_STYLE_SRC = (
    "'self'",
    "data:",
    "'unsafe-inline'",
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
)
CSP_CONNECT_SRC = ("'self'",)
CSP_FONT_SRC = (
    "'self'",
    "fonts.gstatic.com",
)

SPAGHETTI_SAUCE = {
    "apps": [
        "meldingen",
    ],
    "show_fields": False,
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.messages.context_processors.messages",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.static",
                "django.template.context_processors.request",
                "config.context_processors.general_settings",
            ],
        },
    }
]


# Cache settings
REDIS_URL = "redis://redis:6379"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    }
}

WIJKEN_EN_BUURTEN_GEMEENTECODE = "0599"


# Sessions are managed by django-session-timeout-joinup
# Django session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Session settings for django-session-timeout-joinup
SESSION_EXPIRE_MAXIMUM_SECONDS = int(
    os.getenv("SESSION_EXPIRE_MAXIMUM_SECONDS", "28800")
)
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", "3600"))
SESSION_EXPIRE_AFTER_LAST_ACTIVITY_GRACE_PERIOD = int(
    os.getenv("SESSION_EXPIRE_AFTER_LAST_ACTIVITY_GRACE_PERIOD", "1800")
)

DEFAULT_FILE_STORAGE = "utils.storage.FileSystemOverwriteStorage"
THUMBNAIL_CACHE_TIMEOUT = 0
THUMBNAIL_FORCE_OVERWRITE = True
THUMBNAIL_BACKEND = "utils.images.ThumbnailBackend"
THUMBNAIL_PREFIX = "afbeeldingen"
THUMBNAIL_KLEIN = "128x128"
THUMBNAIL_STANDAARD = "1480x1480"
BESTANDEN_PREFIX = "bestanden"
MELDING_AFGESLOTEN_BIJLAGE_OPRUIMEN_SECONDS = int(
    os.getenv(
        "MELDING_AFGESLOTEN_BIJLAGE_OPRUIMEN_SECONDS",
        "3600" if ENVIRONMENT != "production" else "2592000",
    )
)


def show_debug_toolbar(request):
    return DEBUG and os.getenv("SHOW_DEBUG_TOOLBAR") in TRUE_VALUES


DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.history.HistoryPanel",
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.alerts.AlertsPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",
]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": show_debug_toolbar,
    "INSERT_BEFORE": "</head>",
    "IS_RUNNING_TESTS": False,
    "ENABLE_STACKTRACES": True,
    "UPDATE_ON_FETCH": True,
}


LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "/app/uwsgi.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "WARNING" if not DEBUG else "INFO",
            "propagate": False,
        },
    },
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

OIDC_RP_CLIENT_ID = os.getenv("OIDC_RP_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = os.getenv("OIDC_RP_CLIENT_SECRET")

OIDC_REALM = os.getenv("OIDC_REALM")
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL")
OPENID_CONFIG = {}
OPENID_CONFIG_URI_DEFAULT = (
    f"{AUTH_BASE_URL}/realms/{OIDC_REALM}/.well-known/openid-configuration"
    if AUTH_BASE_URL and OIDC_REALM
    else None
)
OPENID_CONFIG_URI = os.getenv(
    "OPENID_CONFIG_URI",
    OPENID_CONFIG_URI_DEFAULT,
)
if OPENID_CONFIG_URI:
    try:
        OPENID_CONFIG = requests.get(
            OPENID_CONFIG_URI,
            headers={
                "user-agent": urllib3.util.SKIP_HEADER,
            },
        ).json()
    except Exception as e:
        raise Exception(f"OPENID_CONFIG FOUT, url: {OPENID_CONFIG_URI}, error: {e}")

OIDC_ENABLED = OPENID_CONFIG and OIDC_RP_CLIENT_ID
if OIDC_ENABLED:
    OIDC_VERIFY_SSL = os.getenv("OIDC_VERIFY_SSL", True) in TRUE_VALUES
    OIDC_USE_NONCE = os.getenv("OIDC_USE_NONCE", True) in TRUE_VALUES

    OIDC_OP_AUTHORIZATION_ENDPOINT = os.getenv(
        "OIDC_OP_AUTHORIZATION_ENDPOINT", OPENID_CONFIG.get("authorization_endpoint")
    )
    OIDC_OP_TOKEN_ENDPOINT = os.getenv(
        "OIDC_OP_TOKEN_ENDPOINT", OPENID_CONFIG.get("token_endpoint")
    )
    OIDC_OP_USER_ENDPOINT = os.getenv(
        "OIDC_OP_USER_ENDPOINT", OPENID_CONFIG.get("userinfo_endpoint")
    )
    OIDC_OP_JWKS_ENDPOINT = os.getenv(
        "OIDC_OP_JWKS_ENDPOINT", OPENID_CONFIG.get("jwks_uri")
    )
    OIDC_RP_SCOPES = os.getenv(
        "OIDC_RP_SCOPES",
        " ".join(OPENID_CONFIG.get("scopes_supported", ["openid", "email", "profile"])),
    )
    OIDC_OP_LOGOUT_ENDPOINT = os.getenv(
        "OIDC_OP_LOGOUT_ENDPOINT",
        OPENID_CONFIG.get("end_session_endpoint"),
    )

    if OIDC_OP_JWKS_ENDPOINT:
        OIDC_RP_SIGN_ALGO = "RS256"

    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
        "apps.authenticatie.auth.OIDCAuthenticationBackend",
    ]

    ALLOW_LOGOUT_GET_METHOD = True
    OIDC_STORE_ID_TOKEN = True
    OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = int(
        os.getenv("OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS", "300")
    )

    LOGIN_REDIRECT_URL = "/"
    LOGIN_REDIRECT_URL_FAILURE = "/"
    LOGOUT_REDIRECT_URL = OIDC_OP_LOGOUT_ENDPOINT
    LOGIN_URL = "/oidc/authenticate/"

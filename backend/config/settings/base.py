from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "apps.common.apps.CommonConfig",
    "apps.routing.apps.RoutingConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.common.middleware.ApiRequestMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "routing-local", "OPTIONS": {"MAX_ENTRIES": 2048}}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOW_CREDENTIALS = False

API_MAX_REQUEST_BYTES = env.int("API_MAX_REQUEST_BYTES", default=65536)
DATA_UPLOAD_MAX_MEMORY_SIZE = API_MAX_REQUEST_BYTES
ROUTING_MAX_LOCATION_LENGTH = env.int("ROUTING_MAX_LOCATION_LENGTH", default=200)
ROUTING_MAX_LOAD_LB = env.int("ROUTING_MAX_LOAD_LB", default=200000)
ROUTING_MAX_CHECKPOINTS = env.int("ROUTING_MAX_CHECKPOINTS", default=1000)
PROVIDER_TIMEOUT_SECONDS = env.float("PROVIDER_TIMEOUT_SECONDS", default=15)
MAPBOX_ACCESS_TOKEN = env.str("MAPBOX_ACCESS_TOKEN", default="")
GEOAPIFY_API_KEY = env.str("GEOAPIFY_API_KEY", default="")
WEATHER_FORECAST_DAYS = env.int("WEATHER_FORECAST_DAYS", default=16)
WEATHER_MAX_LOCATIONS = env.int("WEATHER_MAX_LOCATIONS", default=300)
WEATHER_BATCH_SIZE = env.int("WEATHER_BATCH_SIZE", default=20)
WEATHER_MAX_WORKERS = env.int("WEATHER_MAX_WORKERS", default=3)
WEATHER_CACHE_SECONDS = env.int("WEATHER_CACHE_SECONDS", default=600)
ANALYSIS_CACHE_SECONDS = env.int("ANALYSIS_CACHE_SECONDS", default=900)
CORRIDOR_BUFFER_MILES = env.float("CORRIDOR_BUFFER_MILES", default=15)
CORRIDOR_GRID_MILES = env.float("CORRIDOR_GRID_MILES", default=10)
CORRIDOR_MAX_CELLS = env.int("CORRIDOR_MAX_CELLS", default=min(150, WEATHER_MAX_LOCATIONS))
CORRIDOR_MAX_CANDIDATES = env.int("CORRIDOR_MAX_CANDIDATES", default=10000)
CORRIDOR_MAX_VERTICES = env.int("CORRIDOR_MAX_VERTICES", default=50000)
CORRIDOR_MAX_RADIUS_KM = env.float("CORRIDOR_MAX_RADIUS_KM", default=2000)

if not 1 <= WEATHER_FORECAST_DAYS <= 16 or not 1 <= WEATHER_BATCH_SIZE <= 50:
    raise ImproperlyConfigured("Forecast days must be 1–16 and weather batch size 1–50.")
if not 1 <= WEATHER_MAX_WORKERS <= 8 or min(WEATHER_MAX_LOCATIONS, WEATHER_CACHE_SECONDS, ANALYSIS_CACHE_SECONDS) <= 0:
    raise ImproperlyConfigured("Weather limits/cache durations must be positive; workers must be 1–8.")
if not 1 <= CORRIDOR_BUFFER_MILES <= 100 or not 1 <= CORRIDOR_GRID_MILES <= 100:
    raise ImproperlyConfigured("Corridor buffer and grid spacing must be 1–100 miles.")
if (not 1 <= CORRIDOR_MAX_CELLS <= WEATHER_MAX_LOCATIONS
        or not 1 <= CORRIDOR_MAX_CANDIDATES <= 100000
        or not 2 <= CORRIDOR_MAX_VERTICES <= 100000
        or not 1 <= CORRIDOR_MAX_RADIUS_KM <= 2000):
    raise ImproperlyConfigured("Corridor limits must fit the weather location budget and geographic processing caps.")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "NON_FIELD_ERRORS_KEY": "nonFieldErrors",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Weather-aware routing API",
    "DESCRIPTION": (
        "Phases 1–5: location search, driving routes, arrival-time weather risk, "
        "recommendations, and cached 0–48-hour corridor forecast frames."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "ENUM_NAME_OVERRIDES": {
        "RiskLevelEnum": "apps.routing.domain.choices.RISK_CHOICES",
        "WeatherStatusEnum": "apps.routing.domain.choices.WEATHER_STATUS_CHOICES",
        "PrecipitationUnitEnum": ["in/hr"],
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
    },
}

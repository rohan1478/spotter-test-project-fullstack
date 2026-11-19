from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health

urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    path("api/v1/routes/", include("apps.routing.api.urls")),
    path("api/v1/analyses/", include("apps.routing.api.analysis_urls")),
]

handler400 = "apps.common.views.bad_request"
handler404 = "apps.common.views.not_found"
handler500 = "apps.common.views.server_error"

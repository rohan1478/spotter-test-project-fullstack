from django.urls import path

from .corridor_views import CorridorForecastView

app_name = "analyses"
urlpatterns = [path("<uuid:analysis_id>/corridor-forecast/", CorridorForecastView.as_view(), name="corridor-forecast")]

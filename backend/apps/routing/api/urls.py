from django.urls import path

from .views import CompareRoutesView, PlaceSearchView, RouteOptionsView

app_name = "routing"
urlpatterns = [
    path("compare/", CompareRoutesView.as_view(), name="compare"),
    path("options/", RouteOptionsView.as_view(), name="options"),
    path("places/", PlaceSearchView.as_view(), name="places"),
]

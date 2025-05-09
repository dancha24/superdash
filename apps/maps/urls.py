from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import MapView

urlpatterns = [
    path(
        "maps/leaflet/",
        login_required(MapView.as_view(template_name="maps_leaflet.html")),
        name="maps-leaflet",
    ),
]

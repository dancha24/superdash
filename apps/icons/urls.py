from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import IconsView

urlpatterns = [
    path(
        "icons/ri/",
        login_required(IconsView.as_view(template_name="icons_ri.html")),
        name="icons-ri",
    ),
]

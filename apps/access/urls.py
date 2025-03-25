from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import AccessView

urlpatterns = [
    path(
        "app/access/roles/",
        login_required(AccessView.as_view(template_name="app_access_roles.html")),
        name="app-access-roles",
    ),
    path(
        "app/access/permission/",
        login_required(AccessView.as_view(template_name="app_access_permission.html")),
        name="app-access-permission",
    ),
]

from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import KanbanView

urlpatterns = [
    path(
        "app/kanban/",
        login_required(KanbanView.as_view(template_name="app_kanban.html")),
        name="app-kanban",
    ),
]

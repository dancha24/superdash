from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import CalendarView

urlpatterns = [
    path(
        "app/calendar/",
        login_required(CalendarView.as_view(template_name="app_calendar.html")),
        name="app-calendar",
    ),
]

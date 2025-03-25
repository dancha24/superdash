from django.urls import path

from .views import testView

urlpatterns = [
    path(
        "",
        testView.as_view(template_name="test.html"),
        name="test",
    ),
]

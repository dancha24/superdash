from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import FormValidationView

urlpatterns = [
    path(
        "form/validation/",
        login_required(FormValidationView.as_view(template_name="form_validation.html")),
        name="form-validation",
    ),
]

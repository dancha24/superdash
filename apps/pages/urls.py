from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import PagesView
from .views_misc import MiscPagesView

urlpatterns = [
    path(
        "pages/profile/user/",
        login_required(PagesView.as_view(template_name="pages_profile_user.html")),
        name="pages-profile-user",
    ),
    path(
        "pages/profile/teams/",
        login_required(PagesView.as_view(template_name="pages_profile_teams.html")),
        name="pages-profile-teams",
    ),
    path(
        "pages/profile/projects/",
        login_required(PagesView.as_view(template_name="pages_profile_projects.html")),
        name="pages-profile-projects",
    ),
    path(
        "pages/profile/connections/",
        login_required(PagesView.as_view(template_name="pages_profile_connections.html")),
        name="pages-profile-connections",
    ),
    path(
        "pages/account_settings/account/",
        login_required(PagesView.as_view(template_name="pages_account_settings_account.html")),
        name="pages-account-settings-account",
    ),
    path(
        "pages/account_settings/security/",
        login_required(PagesView.as_view(template_name="pages_account_settings_security.html")),
        name="pages-account-settings-security",
    ),
    path(
        "pages/account_settings/billing/",
        login_required(PagesView.as_view(template_name="pages_account_settings_billing.html")),
        name="pages-account-settings-billing",
    ),
    path(
        "pages/account_settings/notifications/",
        login_required(PagesView.as_view(template_name="pages_account_settings_notifications.html")),
        name="pages-account-settings-notifications",
    ),
    path(
        "pages/account_settings/connections/",
        login_required(PagesView.as_view(template_name="pages_account_settings_connections.html")),
        name="pages-account-settings-connections",
    ),
    path(
        "pages/faq/",
        login_required(PagesView.as_view(template_name="pages_faq.html")),
        name="pages-faq",
    ),
    path(
        "pages/pricing/",
        login_required(PagesView.as_view(template_name="pages_pricing.html")),
        name="pages-pricing",
    ),
    path(
        "pages/misc/error/",
        MiscPagesView.as_view(template_name="pages_misc_error.html"),
        name="pages-misc-error",
    ),
    path(
        "pages/misc/under_maintenance/",
        MiscPagesView.as_view(template_name="pages_misc_under_maintenance.html"),
        name="pages-misc-under-maintenance",
    ),
    path(
        "pages/misc/comingsoon/",
        MiscPagesView.as_view(template_name="pages_misc_comingsoon.html"),
        name="pages-misc-comingsoon",
    ),
    path(
        "pages/misc/not_authorized/",
        MiscPagesView.as_view(template_name="pages_misc_not_authorized.html"),
        name="pages-misc-not-authorized",
    ),
    path(
        "pages/misc/server_error/",
        MiscPagesView.as_view(template_name="pages_misc_server_error.html"),
        name="pages-misc-server-error",
    ),
]

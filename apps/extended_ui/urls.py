from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import ExtendedUiView

urlpatterns = [
    path(
        "extended_ui/avatar/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_avatar.html")),
        name="extended-ui-avatar",
    ),
    path(
        "extended_ui/blockui/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_blockui.html")),
        name="extended-ui-blockui",
    ),
    path(
        "extended_ui/drag_and_drop/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_drag_and_drop.html")),
        name="extended-ui-drag-and-drop",
    ),
    path(
        "extended_ui/media_player/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_media_player.html")),
        name="extended-ui-media-player",
    ),
    path(
        "extended_ui/perfect_scrollbar/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_perfect_scrollbar.html")),
        name="extended-ui-perfect-scrollbar",
    ),
    path(
        "extended_ui/star_ratings/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_star_ratings.html")),
        name="extended-ui-star-ratings",
    ),
    path(
        "extended_ui/sweetalert2/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_sweetalert2.html")),
        name="extended-ui-sweetalert2",
    ),
    path(
        "extended_ui/text_divider/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_text_divider.html")),
        name="extended-ui-text-divider",
    ),
    path(
        "extended_ui/timeline_basic/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_timeline_basic.html")),
        name="extended-ui-timeline-basic",
    ),
    path(
        "extended_ui/timeline_fullscreen/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_timeline_fullscreen.html")),
        name="extended-ui-timeline-fullscreen",
    ),
    path(
        "extended_ui/tour/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_tour.html")),
        name="extended-ui-tour",
    ),
    path(
        "extended_ui/treeview/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_treeview.html")),
        name="extended-ui-treeview",
    ),
    path(
        "extended_ui/misc/",
        login_required(ExtendedUiView.as_view(template_name="extended_ui_misc.html")),
        name="extended-ui-misc",
    ),
]

from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # path("dash/", login_required(views.ReportTest.as_view(template_name="dash/dash.html")), name="dashtest",),
    # path("reports/", login_required(views.ReportList.as_view(template_name="dash/dash.html")), name="reports",),
    # path("reports_seg_site/", login_required(views.ReportSegSite.as_view(template_name="dash/rep_seg_site.html")), name="reports_seg_site",),
    # path("reports_srav/", login_required(views.ReportSrav.as_view(template_name="dash/rep_srav.html")), name="reports_srav",),
    # path("report_obsh/", login_required(views.ReportObsh.as_view(template_name="dash/rep_obsh.html")), name="report_obsh",),
    # path("report_rus/", login_required(views.ReportRus.as_view(template_name="dash/rep_rus.html")), name="report_rus",),
    # path("report_rus_period/", login_required(views.ReportPeriod.as_view(template_name="dash/rep_period.html")), name="report_period",),
    path("dash/", views.ReportTest.as_view(template_name="dash/dash.html"), name="dashtest",),
    path("reports/", views.ReportList.as_view(template_name="dash/dash.html"), name="reports",),
    path("reports_seg_site/", views.ReportSegSite.as_view(template_name="dash/rep_seg_site.html"), name="reports_seg_site",),
    path("reports_srav/", views.ReportSrav.as_view(template_name="dash/rep_srav.html"), name="reports_srav",),
    path("report_obsh/", views.ReportObsh.as_view(template_name="dash/rep_obsh.html"), name="report_obsh",),
    path("report_rus/", views.ReportRus.as_view(template_name="dash/rep_rus.html"), name="report_rus",),
    path("report_rus_period/", views.ReportPeriod.as_view(template_name="dash/rep_period.html"), name="report_period",),
]

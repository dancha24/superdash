from django.urls import path

from . import views

urlpatterns = [
    path("dash/", views.ReportTest.as_view(template_name="dash/dash.html"), name="dashtest",),
    path("reports/", views.ReportList.as_view(template_name="dash/dash.html"), name="reports",),
    path("reports_seg_site/", views.ReportSegSite.as_view(template_name="dash/rep_seg_site.html"), name="reports_seg_site",),
    path("reports_srav/", views.ReportSrav.as_view(template_name="dash/rep_srav.html"), name="reports_srav",),
    path("report_obsh/", views.ReportObsh.as_view(template_name="dash/rep_obsh.html"), name="report_obsh",),
    path("report_rus/", views.ReportRus.as_view(template_name="dash/rep_rus.html"), name="report_rus",),
]

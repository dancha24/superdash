import logging
from datetime import datetime

from django.views.generic import TemplateView

from web_project import TemplateLayout

from .models import Report
from .utils import get_report_data, get_report_data_by_two_periods

logger = logging.getLogger(__name__)


def filters(self, iterat=''):
    year = tuple(self.request.GET.getlist('year' + iterat))
    month = tuple(map(int, self.request.GET.getlist('month' + iterat)))
    segment = tuple(self.request.GET.getlist('segment' + iterat))
    site = tuple(self.request.GET.getlist('site' + iterat))

    return year, month, segment, site


class ReportList(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year, month, segment, site = filters(self)

        reports = Report.objects.all()

        if year:
            reports = reports.filter(start_period__year__in=year)
        if month:
            reports = reports.filter(start_period__month__in=month)
        if segment:
            reports = reports.filter(segment__in=segment)
        if site:
            reports = reports.filter(site__in=site)

        years = Report.get_years()
        months = Report.get_months()
        segments = Report.get_segments()
        sites = Report.get_sites()

        # Суммарные показатели
        total_data = Report.get_total_data(year=year, month=month, segment=segment, site=site)

        # Вычисления для отображения
        presentation_data = Report.get_presentation_data(year=year, month=month, segment=segment, site=site)

        # Добавим дополнительные значения для шаблона с округлением
        additional_data = Report.get_additional_data(year=year, month=month, segment=segment, site=site)

        context.update({
            'reports': reports,
            'years': years,
            'months': months,
            'segments': segments,
            'sites': sites,
            'year': year,
            'month': month,
            'segment': segment,
            'site': site,
            **total_data,
            **presentation_data,
            **additional_data,
        })

        return context


class ReportSegSite(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year, month, segment, site = filters(self)

        report_data = get_report_data(year, month, segment, site)

        context.update({
            'title': 'Отчет по сегментам и сайтам ' + str(month) + ' ' + str(year),
            **report_data,
        })

        return context


class ReportSrav(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # 1 фильтр
        year, month, segment, site = filters(self)  # получаем фильтры из адресной строки

        # 2 фильтр
        year2, month2, segment2, site2 = filters(self, '2')

        report_data = get_report_data_by_two_periods([year, month, segment, site], [year2, month2, segment2, site2])

        context.update({
            'title': 'Отчет сравнение периодов ' + str(month) + ' ' + str(year) + ' ' + str(month2) + ' ' + str(year2),
            **report_data,
        })

        return context


class ReportObsh(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year, month, segment, site = filters(self)

        report_data = get_report_data(year, month, segment, site)

        context.update({
            'title': 'Общие показатели за ' + str(month) + ' ' + str(year),
            **report_data
        })

        return context


class ReportRus(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year, month, segment, site = filters(self)  # получаем фильтры из адресной строки
        year, month = list(year), list(month)

        if not month:
            if datetime.now().month == 1:
                month.append(12)
                year.append(datetime.now().year - 1)
            else:
                year.append(datetime.now().year)
                month.append(datetime.now().month - 1)

        year, month = tuple(year), tuple(month)

        # Получаем текущий год и месяц
        current_year = int(year[0]) if year else datetime.now().year
        current_month = int(month[0]) if month else datetime.now().month

        year2 = []
        month2 = []
        segment2 = tuple()
        site2 = tuple()

        # Вычисляем предыдущий месяц
        if current_month == 1:
            year2.append(current_year - 1)
            month2.append(12)
        else:
            year2.append(current_year)
            month2.append(current_month - 1)

        year2, month2 = tuple(year2), tuple(month2)

        report_data = get_report_data_by_two_periods([year, month, segment, site], [year2, month2, segment2, site2])

        context.update({
            'title': 'Отчет сравнение периодов ' + str(month) + ' ' + str(year) + ' ' + str(month2) + ' ' + str(year2),
            **report_data
        })

        return context


class ReportTest(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        reports = Report.objects.all()
        reports = reports.filter(start_period__year=2024)
        reports = reports.filter(segment="Директ")
        reports = reports.filter(site="Одинцово")
        reports = reports.filter(start_period__month__in=[1, 2, 3, 4, 5, 6])

        budget = Report.get_name_list('leads', reports)
        revenue = Report.get_name_list('deals', reports)

        context.update({
            'title': 'Тест отчета 1',
            'total_budget': Report.total_sum_column('budget'),
            'total_revenue': Report.total_sum_column('revenue'),
            'total_deals': Report.total_sum_column('deals'),
            'budget': budget,
            'revenue': revenue,
        })

        return context

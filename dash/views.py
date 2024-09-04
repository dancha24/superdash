from django.shortcuts import render
from .models import Report
from django.db.models.functions import ExtractMonth, ExtractYear
from django.db.models import Sum, Avg
from django.http import QueryDict
from django.db.models import Avg, F, FloatField, ExpressionWrapper, Case, When
from django.db.models.functions import Coalesce
from django.views.generic import TemplateView
from web_project import TemplateLayout
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MONTHS = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}


def report_list(request):
    year = request.GET.getlist('year')
    month = request.GET.getlist('month')
    segment = request.GET.getlist('segment')
    site = request.GET.getlist('site')

    reports = Report.objects.all()

    if year:
        reports = reports.filter(start_period__year__in=year)
    if month:
        reports = reports.filter(start_period__month__in=month)
    if segment:
        reports = reports.filter(segment__in=segment)
    if site:
        reports = reports.filter(site__in=site)

    years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                     flat=True).distinct().order_by(
        'month')
    segments = Report.objects.values_list('segment', flat=True).distinct()
    sites = Report.objects.values_list('site', flat=True).distinct()

    months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                  'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals = reports.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                     'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
    avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                             2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
    roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                            2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                           2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                  2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                       2) if total_qualified_deals > 0 else None  # Общий Средний чек
    conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                        2) if total_leads > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                    2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                            2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                         2) if total_deals > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                 2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
        float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                          2) if total_deals > 0 else None  # Общий Упущенная прибыль

    context = {
        'reports': reports,
        'years': years,
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        'total_budget': total_budget,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'total_unqualified_leads': total_unqualified_leads,
        'total_deals': total_deals,
        'total_qualified_deals': total_qualified_deals,
        'total_failed_deals': total_failed_deals,
        'total_ignored_failed_deals': total_ignored_failed_deals,
        'total_revenue': total_revenue,
        'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
        'avg_cpa_lead': avg_cpa_lead,
        'avg_cpa_deal': avg_cpa_deal,
        'avg_cpa_won_deal': avg_cpa_won_deal,
        'roi': roi,
        'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
        'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
        'direct_losses_ignored': direct_losses_ignored,
        'missed_profit': missed_profit,
        'revenue_per_qualified_deal': revenue_per_qualified_deal,
        'conversion_rate_unqualified': conversion_rate_unqualified,
        'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
        'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
        'conversion_rate_failed_deals': conversion_rate_failed_deals,
        'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
    }

    return render(request, 'dash/dash.html', context)


def report_month(request):
    year = request.GET.getlist('year')
    month = request.GET.getlist('month')
    segment = request.GET.getlist('segment')
    site = request.GET.getlist('site')

    reports = Report.objects.all()

    if year:
        reports = reports.filter(start_period__year__in=year)
    if month:
        reports = reports.filter(start_period__month__in=month)
    if segment:
        reports = reports.filter(segment__in=segment)
    if site:
        reports = reports.filter(site__in=site)

    years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                     flat=True).distinct().order_by(
        'month')
    segments = Report.objects.values_list('segment', flat=True).distinct()
    sites = Report.objects.values_list('site', flat=True).distinct()

    months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    year2 = request.GET.getlist('year2')
    month2 = request.GET.getlist('month2')
    segment2 = request.GET.getlist('segment2')
    site2 = request.GET.getlist('site2')

    reports2 = Report.objects.all()

    if year2:
        reports2 = reports2.filter(start_period__year__in=year2)
    if month2:
        reports2 = reports2.filter(start_period__month__in=month2)
    if segment2:
        reports2 = reports2.filter(segment__in=segment2)
    if site2:
        reports2 = reports2.filter(site__in=site2)

    years2 = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months2 = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                      flat=True).distinct().order_by(
        'month')
    segments2 = Report.objects.values_list('segment', flat=True).distinct()
    sites2 = Report.objects.values_list('site', flat=True).distinct()

    months2 = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                  'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals = reports.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                     'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
    avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                             2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
    roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                            2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                           2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                  2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                       2) if total_qualified_deals > 0 else None  # Общий Средний чек
    conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                        2) if total_leads > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                    2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                            2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                         2) if total_deals > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                 2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
        float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                          2) if total_deals > 0 else None  # Общий Упущенная прибыль

    context = {
        'reports': reports,
        'years': years,
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        'reports2': reports2,
        'years2': years2,
        'months2': months2,
        'segments2': segments2,
        'sites2': sites2,
        'year2': year2,
        'month2': month2,
        'segment2': segment2,
        'site2': site2,
        'total_budget': total_budget,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'total_unqualified_leads': total_unqualified_leads,
        'total_deals': total_deals,
        'total_qualified_deals': total_qualified_deals,
        'total_failed_deals': total_failed_deals,
        'total_ignored_failed_deals': total_ignored_failed_deals,
        'total_revenue': total_revenue,
        'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
        'avg_cpa_lead': avg_cpa_lead,
        'avg_cpa_deal': avg_cpa_deal,
        'avg_cpa_won_deal': avg_cpa_won_deal,
        'roi': roi,
        'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
        'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
        'direct_losses_ignored': direct_losses_ignored,
        'missed_profit': missed_profit,
        'revenue_per_qualified_deal': revenue_per_qualified_deal,
        'conversion_rate_unqualified': conversion_rate_unqualified,
        'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
        'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
        'conversion_rate_failed_deals': conversion_rate_failed_deals,
        'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
    }

    return render(request, 'dash/report_seg_site.html', context)


def report_seg_site(request):
    year = request.GET.getlist('year')
    month = request.GET.getlist('month')
    segment = request.GET.getlist('segment')
    site = request.GET.getlist('site')

    reports = Report.objects.all()

    if year:
        reports = reports.filter(start_period__year__in=year)
    if month:
        reports = reports.filter(start_period__month__in=month)
    if segment:
        reports = reports.filter(segment__in=segment)
    if site:
        reports = reports.filter(site__in=site)

    years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                     flat=True).distinct().order_by(
        'month')
    segments = Report.objects.values_list('segment', flat=True).distinct()
    sites = Report.objects.values_list('site', flat=True).distinct()

    months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    year2 = request.GET.getlist('year2')
    month2 = request.GET.getlist('month2')
    segment2 = request.GET.getlist('segment2')
    site2 = request.GET.getlist('site2')

    reports2 = Report.objects.all()

    if year2:
        reports2 = reports2.filter(start_period__year__in=year2)
    if month2:
        reports2 = reports2.filter(start_period__month__in=month2)
    if segment2:
        reports2 = reports2.filter(segment__in=segment2)
    if site2:
        reports2 = reports2.filter(site__in=site2)

    years2 = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months2 = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                      flat=True).distinct().order_by(
        'month')
    segments2 = Report.objects.values_list('segment', flat=True).distinct()
    sites2 = Report.objects.values_list('site', flat=True).distinct()

    months2 = sorted([(m, MONTHS[m]) for m in months2 if m in MONTHS.keys()])

    avg_missed_profit_igore = 0
    count_missed_profit = 0
    for rep in reports:
        avg_missed_profit_igore += rep.missed_profit
        count_missed_profit += 1
    avg_missed_profit_igore = avg_missed_profit_igore / count_missed_profit

    avg_direct_losses_ignored = 0
    count_avg_direct_losses_ignored = 0
    for rep in reports:
        avg_direct_losses_ignored += rep.direct_losses_ignored
        count_avg_direct_losses_ignored += 1
    avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

    # суммарные показатели

    total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or None  # Сумма лидов
    total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                  'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals = reports.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                     'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else 0  # Общий CPA Лида
    avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else 0  # Общий CPA Сделки
    avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                             2) if total_deals > 0 else 0  # Общий CPA Выигранной Сделки
    roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                            2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                           2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                  2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                       2) if total_qualified_deals > 0 else None  # Общий Средний чек
    conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                        2) if total_leads > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                    2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                            2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                         2) if total_deals > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                 2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
        float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                          2) if total_deals > 0 else None  # Общий Упущенная прибыль

    # Средние показатели

    avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
    avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
    avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
    avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                'unqualified_leads__avg'] or 0  # Среднее некач. лидов
    avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
    avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                              'qualified_deals__avg'] or 0  # Среднее качественных сделок
    avg_failed_deals = reports.aggregate(Avg('failed_deals'))['failed_deals__avg'] or 0  # Среднее проваленных сделок
    avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                   'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
    avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки
    # avg_missed_profit = reports.aggregate(Avg('missed_profit'))['missed_profit__avg'] or 0  # Среднее упущенной прибыли

    # # Вычисления для отображения
    # avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Среднее CPA Лида
    # avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Среднее CPA Сделки
    # avg_cpa_won_deal = round(total_budget / total_qualified_deals,
    #                          2) if total_deals > 0 else None  # Среднее CPA Выигранной Сделки
    # roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Среднее РОЙ
    # conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
    #                                         2) if total_clicks > 0 else None  # Среднее CR% Кликов в Лиды
    # conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
    #                                        2) if total_leads > 0 else None  # Среднее CR% Лидов в Сделки
    # direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
    #                               2)  # Среднее Потери прямые по причине игнора дел
    #
    # # Добавим дополнительные значения для шаблона с округлением
    # revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
    #                                    2) if total_qualified_deals > 0 else None  # Среднее Средний чек
    # conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
    #                                     2) if total_leads > 0 else None  # Среднее CR% некач. Лидов
    # conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
    #                                                 2) if total_deals > 0 else None  # % Среднее % конверсии Обращений в Сделку качественную
    # conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
    #                                         2) if total_deals > 0 else None  # % Среднее конверсии в Сделку качественную (после стадии "Встреча")
    # conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
    #                                      2) if total_deals > 0 else None  # Среднее % провала Сделок
    # conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
    #                                              2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел
    #
    # missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
    #     float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
    #                       2) if total_deals > 0 else None  # Среднее Упущенная прибыль

    context = {
        'title': 'Отчет по сегментам и сайтам ' + str(month) + ' ' + str(year),
        'reports': reports,
        'years': years,
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        'reports2': reports2,
        'years2': years2,
        'months2': months2,
        'segments2': segments2,
        'sites2': sites2,
        'year2': year2,
        'month2': month2,
        'segment2': segment2,
        'site2': site2,
        'total_budget': total_budget,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'total_unqualified_leads': total_unqualified_leads,
        'total_deals': total_deals,
        'total_qualified_deals': total_qualified_deals,
        'total_failed_deals': total_failed_deals,
        'total_ignored_failed_deals': total_ignored_failed_deals,
        'total_revenue': total_revenue,
        'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
        'avg_cpa_lead': avg_cpa_lead,
        'avg_cpa_deal': avg_cpa_deal,
        'avg_cpa_won_deal': avg_cpa_won_deal,
        'roi': roi,
        'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
        'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
        'direct_losses_ignored': direct_losses_ignored,
        'missed_profit': missed_profit,
        'revenue_per_qualified_deal': revenue_per_qualified_deal,
        'conversion_rate_unqualified': conversion_rate_unqualified,
        'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
        'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
        'conversion_rate_failed_deals': conversion_rate_failed_deals,
        'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
        # передаем средние
        'avg_budget': avg_budget,
        'avg_clicks': avg_clicks,
        'avg_leads': avg_leads,
        'avg_unqualified_leads': avg_unqualified_leads,
        'avg_deals': avg_deals,
        'avg_qualified_deals': avg_qualified_deals,
        'avg_failed_deals': avg_failed_deals,
        'avg_ignored_failed_deals': avg_ignored_failed_deals,
        'avg_revenue': avg_revenue,
        'avg_missed_profit_igore': avg_missed_profit_igore,
        'avg_direct_losses_ignored': avg_direct_losses_ignored,
    }

    return render(request, 'dash/report_seg_site.html', context)


def report_srav(request):
    year = request.GET.getlist('year')
    month = request.GET.getlist('month')
    segment = request.GET.getlist('segment')
    site = request.GET.getlist('site')

    reports = Report.objects.all()

    if year:
        reports = reports.filter(start_period__year__in=year)
    if month:
        reports = reports.filter(start_period__month__in=month)
    if segment:
        reports = reports.filter(segment__in=segment)
    if site:
        reports = reports.filter(site__in=site)

    years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                     flat=True).distinct().order_by(
        'month')
    segments = Report.objects.values_list('segment', flat=True).distinct()
    sites = Report.objects.values_list('site', flat=True).distinct()

    months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    year2 = request.GET.getlist('year2')
    month2 = request.GET.getlist('month2')
    segment2 = request.GET.getlist('segment2')
    site2 = request.GET.getlist('site2')

    reports2 = Report.objects.all()

    if year2:
        reports2 = reports2.filter(start_period__year__in=year2)
    if month2:
        reports2 = reports2.filter(start_period__month__in=month2)
    if segment2:
        reports2 = reports2.filter(segment__in=segment2)
    if site2:
        reports2 = reports2.filter(site__in=site2)

    years2 = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months2 = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                      flat=True).distinct().order_by(
        'month')
    segments2 = Report.objects.values_list('segment', flat=True).distinct()
    sites2 = Report.objects.values_list('site', flat=True).distinct()

    months2 = sorted([(m, MONTHS[m]) for m in months2 if m in MONTHS.keys()])

    avg_missed_profit_igore = 0
    count_missed_profit = 0
    for rep in reports:
        avg_missed_profit_igore += rep.missed_profit
        count_missed_profit += 1
    avg_missed_profit_igore = avg_missed_profit_igore / count_missed_profit

    avg_direct_losses_ignored = 0
    count_avg_direct_losses_ignored = 0
    for rep in reports:
        avg_direct_losses_ignored += rep.direct_losses_ignored
        count_avg_direct_losses_ignored += 1
    avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

    # Для периода 1
    # суммарные показатели

    total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                  'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals = reports.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                     'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
    avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                             2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
    roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                            2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                           2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                  2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                       2) if total_qualified_deals > 0 else None  # Общий Средний чек
    conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                        2) if total_leads > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                    2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                            2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                         2) if total_deals > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                 2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
        float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                          2) if total_deals > 0 else None  # Общий Упущенная прибыль

    # Средние показатели

    avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
    avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
    avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
    avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                'unqualified_leads__avg'] or 0  # Среднее некач. лидов
    avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
    avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                              'qualified_deals__avg'] or 0  # Среднее качественных сделок
    avg_failed_deals = reports.aggregate(Avg('failed_deals'))['failed_deals__avg'] or 0  # Среднее проваленных сделок
    avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                   'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
    avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

    # Для периода 2
    # суммарные показатели

    total_budget2 = reports2.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks2 = reports2.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads2 = reports2.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads2 = reports2.aggregate(Sum('unqualified_leads'))[
                                   'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals2 = reports2.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals2 = reports2.aggregate(Sum('qualified_deals'))[
                                 'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals2 = reports2.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals2 = reports2.aggregate(Sum('ignored_failed_deals'))[
                                      'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue2 = reports2.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead2 = round(total_budget2 / total_leads2, 2) if total_leads2 > 0 else None  # Общий CPA Лида
    avg_cpa_deal2 = round(total_budget2 / total_deals2, 2) if total_deals2 > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal2 = round(total_budget2 / total_qualified_deals2,
                              2) if total_deals2 > 0 else None  # Общий CPA Выигранной Сделки
    roi2 = round((total_revenue2 - total_budget2) / total_budget2 * 100, 2) if total_budget2 > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads2 = round((total_leads2 / total_clicks2 * 100),
                                             2) if total_clicks2 > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals2 = round((total_deals2 / total_leads2 * 100),
                                            2) if total_leads2 > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored2 = round(total_ignored_failed_deals2 * (avg_cpa_deal2 or 0),
                                   2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal2 = round(total_revenue2 / total_qualified_deals2,
                                        2) if total_qualified_deals2 > 0 else None  # Общий Средний чек
    conversion_rate_unqualified2 = round((total_unqualified_leads2 / total_leads2 * 100),
                                         2) if total_leads2 > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals2 = round((total_qualified_deals2 / total_leads2 * 100),
                                                     2) if total_deals2 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals2 = round((total_qualified_deals2 / total_deals2 * 100),
                                             2) if total_deals2 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals2 = round((total_failed_deals2 / total_deals2 * 100),
                                          2) if total_deals2 > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals2 = round((total_ignored_failed_deals2 / total_deals2 * 100),
                                                  2) if total_deals2 > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit2 = round(((total_ignored_failed_deals2 * conversion_rate_qualified_deals2 / 100) * (
        float(revenue_per_qualified_deal2) if revenue_per_qualified_deal2 is not None else 0)),
                           2) if total_deals2 > 0 else None  # Общий Упущенная прибыль

    # Для суммарного периода
    # суммарные показатели

    total_budget3 = total_budget + total_budget2
    total_clicks3 = total_clicks + total_clicks2  # Сумма кликов
    total_leads3 = total_leads + total_leads2
    total_unqualified_leads3 = total_unqualified_leads + total_unqualified_leads2  # Сумма некач. лидов
    total_deals3 = total_deals + total_deals2  # Сумма качественных сделок
    total_qualified_deals3 = total_qualified_deals + total_qualified_deals2  # Сумма качественных сделок
    total_failed_deals3 = total_failed_deals + total_failed_deals2  # Сумма проваленных сделок
    total_ignored_failed_deals3 = total_ignored_failed_deals + total_ignored_failed_deals2  # Сумма некач. сделок игнор
    total_revenue3 = total_revenue + total_revenue2  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead3 = round(total_budget3 / total_leads3, 2) if total_leads3 > 0 else None  # Общий CPA Лида
    avg_cpa_deal3 = round(total_budget3 / total_deals3, 2) if total_deals3 > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal3 = round(total_budget3 / total_qualified_deals3,
                              2) if total_deals3 > 0 else None  # Общий CPA Выигранной Сделки
    roi3 = round((total_revenue3 - total_budget3) / total_budget3 * 100, 2) if total_budget3 > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads3 = round((total_leads3 / total_clicks3 * 100),
                                             2) if total_clicks3 > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals3 = round((total_deals3 / total_leads3 * 100),
                                            2) if total_leads3 > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored3 = round(total_ignored_failed_deals3 * (avg_cpa_deal3 or 0),
                                   2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal3 = round(total_revenue3 / total_qualified_deals3,
                                        2) if total_qualified_deals3 > 0 else None  # Общий Средний чек
    conversion_rate_unqualified3 = round((total_unqualified_leads3 / total_leads3 * 100),
                                         2) if total_leads3 > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals3 = round((total_qualified_deals3 / total_leads3 * 100),
                                                     2) if total_deals3 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals3 = round((total_qualified_deals3 / total_deals3 * 100),
                                             2) if total_deals3 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals3 = round((total_failed_deals3 / total_deals3 * 100),
                                          2) if total_deals3 > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals3 = round((total_ignored_failed_deals3 / total_deals3 * 100),
                                                  2) if total_deals3 > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit3 = round(((total_ignored_failed_deals3 * conversion_rate_qualified_deals3 / 100) * (
        float(revenue_per_qualified_deal3) if revenue_per_qualified_deal3 is not None else 0)),
                           2) if total_deals3 > 0 else None  # Общий Упущенная прибыль

    # Средние показатели

    avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
    avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
    avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
    avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                'unqualified_leads__avg'] or 0  # Среднее некач. лидов
    avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
    avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                              'qualified_deals__avg'] or 0  # Среднее качественных сделок
    avg_failed_deals = reports.aggregate(Avg('failed_deals'))['failed_deals__avg'] or 0  # Среднее проваленных сделок
    avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                   'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
    avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

    context = {
        'title': 'Отчет сравнение периодов ' + str(month) + ' ' + str(year) + ' ' + str(month2) + ' ' + str(year2),

        # для периода 1
        'reports': reports,
        'years': years,
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        'total_budget': total_budget,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'total_unqualified_leads': total_unqualified_leads,
        'total_deals': total_deals,
        'total_qualified_deals': total_qualified_deals,
        'total_failed_deals': total_failed_deals,
        'total_ignored_failed_deals': total_ignored_failed_deals,
        'total_revenue': total_revenue,
        'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
        'avg_cpa_lead': avg_cpa_lead,
        'avg_cpa_deal': avg_cpa_deal,
        'avg_cpa_won_deal': avg_cpa_won_deal,
        'roi': roi,
        'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
        'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
        'direct_losses_ignored': direct_losses_ignored,
        'missed_profit': missed_profit,
        'revenue_per_qualified_deal': revenue_per_qualified_deal,
        'conversion_rate_unqualified': conversion_rate_unqualified,
        'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
        'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
        'conversion_rate_failed_deals': conversion_rate_failed_deals,
        'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
        # передаем средние
        'avg_budget': avg_budget,
        'avg_clicks': avg_clicks,
        'avg_leads': avg_leads,
        'avg_unqualified_leads': avg_unqualified_leads,
        'avg_deals': avg_deals,
        'avg_qualified_deals': avg_qualified_deals,
        'avg_failed_deals': avg_failed_deals,
        'avg_ignored_failed_deals': avg_ignored_failed_deals,
        'avg_revenue': avg_revenue,
        'avg_missed_profit_igore': avg_missed_profit_igore,
        # 'avg_direct_losses_ignored': avg_direct_losses_ignored,

        # для периода 2

        'reports2': reports2,
        'years2': years2,
        'months2': months2,
        'segments2': segments2,
        'sites2': sites2,
        'year2': year2,
        'month2': month2,
        'segment2': segment2,
        'site2': site2,
        'total_budget2': total_budget2,
        'total_clicks2': total_clicks2,
        'total_leads2': total_leads2,
        'total_unqualified_leads2': total_unqualified_leads2,
        'total_deals2': total_deals2,
        'total_qualified_deals2': total_qualified_deals2,
        'total_failed_deals2': total_failed_deals2,
        'total_ignored_failed_deals2': total_ignored_failed_deals2,
        'total_revenue2': total_revenue2,
        'average_conversion_rate2': f"{round((total_leads2 / total_clicks2) * 100, 2)}%" if total_clicks2 > 0 else "Н/Д",
        'avg_cpa_lead2': avg_cpa_lead2,
        'avg_cpa_deal2': avg_cpa_deal2,
        'avg_cpa_won_deal2': avg_cpa_won_deal2,
        'roi2': roi2,
        'conversion_rate_clicks_to_leads2': conversion_rate_clicks_to_leads2,
        'conversion_rate_leads_to_deals2': conversion_rate_leads_to_deals2,
        'direct_losses_ignored2': direct_losses_ignored2,
        'missed_profit2': missed_profit2,
        'revenue_per_qualified_deal2': revenue_per_qualified_deal2,
        'conversion_rate_unqualified2': conversion_rate_unqualified2,
        'conversion_rate_qualified_leds_to_deals2': conversion_rate_qualified_leds_to_deals2,
        'conversion_rate_qualified_deals2': conversion_rate_qualified_deals2,
        'conversion_rate_failed_deals2': conversion_rate_failed_deals2,
        'conversion_rate_ignored_failed_deals2': conversion_rate_ignored_failed_deals2,

        # Общие средние

        'avg_total_budget': (total_budget + total_budget2) / 2,
        'avg_total_clicks': (total_clicks + total_clicks2) / 2,
        'avg_total_leads': (total_leads + total_leads2) / 2,
        'avg_total_unqualified_leads': (total_unqualified_leads + total_unqualified_leads2) / 2,
        'avg_total_deals': (total_deals + total_deals2) / 2,
        'avg_total_qualified_deals': (total_qualified_deals + total_qualified_deals2) / 2,
        'avg_total_failed_deals': (total_failed_deals + total_failed_deals2) / 2,
        'avg_total_ignored_failed_deals': (total_ignored_failed_deals + total_ignored_failed_deals2) / 2,
        'avg_total_revenue': (total_revenue + total_revenue2) / 2,
        'avg_avg_cpa_lead': (avg_cpa_lead + avg_cpa_lead2) / 2,
        'avg_avg_cpa_deal': (avg_cpa_deal + avg_cpa_deal2) / 2,
        'avg_avg_cpa_won_deal': (avg_cpa_won_deal + avg_cpa_won_deal2) / 2,
        'avg_roi': (roi + roi2) / 2,
        'avg_conversion_rate_clicks_to_leads': (
                                                   conversion_rate_clicks_to_leads + conversion_rate_clicks_to_leads2) / 2,
        'avg_conversion_rate_leads_to_deals': (conversion_rate_leads_to_deals + conversion_rate_leads_to_deals2) / 2,
        'avg_direct_losses_ignored': (direct_losses_ignored + direct_losses_ignored2) / 2,
        'avg_missed_profit': (missed_profit + missed_profit2) / 2,
        'avg_revenue_per_qualified_deal': (revenue_per_qualified_deal + revenue_per_qualified_deal2) / 2,
        'avg_conversion_rate_unqualified': (conversion_rate_unqualified + conversion_rate_unqualified2) / 2,
        'avg_conversion_rate_qualified_leds_to_deals': (
                                                           conversion_rate_qualified_leds_to_deals + conversion_rate_qualified_leds_to_deals2) / 2,
        'avg_conversion_rate_qualified_deals': (
                                                   conversion_rate_qualified_deals + conversion_rate_qualified_deals2) / 2,
        'avg_conversion_rate_failed_deals': (conversion_rate_failed_deals + conversion_rate_failed_deals2) / 2,
        'avg_conversion_rate_ignored_failed_deals': (
                                                        conversion_rate_ignored_failed_deals + conversion_rate_ignored_failed_deals2) / 2,

        # Общяя сумма

        'sum_total_budget': total_budget + total_budget2,
        'sum_total_clicks': total_clicks + total_clicks2,
        'sum_total_leads': total_leads + total_leads2,
        'sum_total_unqualified_leads': total_unqualified_leads + total_unqualified_leads2,
        'sum_total_deals': total_deals + total_deals2,
        'sum_total_qualified_deals': total_qualified_deals + total_qualified_deals2,
        'sum_total_failed_deals': total_failed_deals + total_failed_deals2,
        'sum_total_ignored_failed_deals': total_ignored_failed_deals3,
        'sum_total_revenue': total_revenue + total_revenue2,
        'sum_avg_cpa_lead': avg_cpa_lead3,
        'sum_avg_cpa_deal': avg_cpa_deal3,
        'sum_avg_cpa_won_deal': avg_cpa_won_deal3,
        'sum_roi': roi3,

        'sum_conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads3,
        'sum_conversion_rate_leads_to_deals': conversion_rate_leads_to_deals3,
        'sum_direct_losses_ignored': direct_losses_ignored + direct_losses_ignored2,
        'sum_missed_profit': missed_profit + missed_profit2,
        'sum_revenue_per_qualified_deal': revenue_per_qualified_deal3,
        'sum_conversion_rate_unqualified': conversion_rate_unqualified3,
        'sum_conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals3,
        'sum_conversion_rate_qualified_deals': conversion_rate_qualified_deals3,
        'sum_conversion_rate_failed_deals': conversion_rate_failed_deals3,
        'sum_conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals3,

        # Изменения

        'rost_total_budget': round((total_budget2 - total_budget) / total_budget * 100, 2),
        'rost_total_clicks': round((total_clicks2 - total_clicks) / total_clicks * 100, 2),
        'rost_total_leads': round((total_leads2 - total_leads) / total_leads * 100, 2),
        'rost_total_unqualified_leads': round(
            (total_unqualified_leads2 - total_unqualified_leads) / total_unqualified_leads * 100, 2),
        'rost_total_deals': round((total_deals2 - total_deals) / total_deals * 100, 2),
        'rost_total_qualified_deals': round(
            (total_qualified_deals2 - total_qualified_deals) / total_qualified_deals * 100, 2),
        'rost_total_failed_deals': round((total_failed_deals2 - total_failed_deals) / total_failed_deals * 100, 2),
        'rost_total_ignored_failed_deals': round(
            (total_ignored_failed_deals2 - total_ignored_failed_deals) / total_ignored_failed_deals * 100, 2),
        'rost_total_revenue': round((total_revenue2 - total_revenue) / total_revenue * 100, 2),
        'rost_avg_cpa_lead': round((avg_cpa_lead2 - avg_cpa_lead) / avg_cpa_lead * 100, 2),
        'rost_avg_cpa_deal': round((avg_cpa_deal2 - avg_cpa_deal) / avg_cpa_deal * 100, 2),
        'rost_avg_cpa_won_deal': round((avg_cpa_won_deal2 - avg_cpa_won_deal) / avg_cpa_won_deal * 100, 2),
        'rost_roi': round((roi2 - roi) / roi * 100, 2),
        'rost_conversion_rate_clicks_to_leads': round((
                                                          conversion_rate_clicks_to_leads2 - conversion_rate_clicks_to_leads) / conversion_rate_clicks_to_leads * 100,
                                                      2),
        'rost_conversion_rate_leads_to_deals': round(
            (conversion_rate_leads_to_deals2 - conversion_rate_leads_to_deals) / conversion_rate_leads_to_deals * 100,
            2),
        'rost_direct_losses_ignored': round(
            (direct_losses_ignored2 - direct_losses_ignored) / direct_losses_ignored * 100, 2),
        'rost_missed_profit': round((missed_profit2 - missed_profit) / missed_profit * 100, 2),
        'rost_revenue_per_qualified_deal': round(
            (revenue_per_qualified_deal2 - revenue_per_qualified_deal) / revenue_per_qualified_deal * 100, 2),
        'rost_conversion_rate_unqualified': round(
            (conversion_rate_unqualified2 - conversion_rate_unqualified) / conversion_rate_unqualified * 100, 2),
        'rost_conversion_rate_qualified_leds_to_deals': round((
                                                                  conversion_rate_qualified_leds_to_deals2 - conversion_rate_qualified_leds_to_deals) / conversion_rate_qualified_leds_to_deals * 100,
                                                              2),
        'rost_conversion_rate_qualified_deals': round((
                                                          conversion_rate_qualified_deals2 - conversion_rate_qualified_deals) / conversion_rate_qualified_deals * 100,
                                                      2),
        'rost_conversion_rate_failed_deals': round(
            (conversion_rate_failed_deals2 - conversion_rate_failed_deals) / conversion_rate_failed_deals * 100, 2),
        'rost_conversion_rate_ignored_failed_deals': round((
                                                               conversion_rate_ignored_failed_deals2 - conversion_rate_ignored_failed_deals) / conversion_rate_ignored_failed_deals * 100,
                                                           2),
    }

    return render(request, 'dash/report_srav.html', context)


def report_obsh(request):
    year = request.GET.getlist('year')
    month = request.GET.getlist('month')
    segment = request.GET.getlist('segment')
    site = request.GET.getlist('site')

    reports = Report.objects.all()

    if year:
        reports = reports.filter(start_period__year__in=year)
    if month:
        reports = reports.filter(start_period__month__in=month)
    if segment:
        reports = reports.filter(segment__in=segment)
    if site:
        reports = reports.filter(site__in=site)

    years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                     flat=True).distinct().order_by(
        'month')
    segments = Report.objects.values_list('segment', flat=True).distinct()
    sites = Report.objects.values_list('site', flat=True).distinct()

    months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    year2 = request.GET.getlist('year2')
    month2 = request.GET.getlist('month2')
    segment2 = request.GET.getlist('segment2')
    site2 = request.GET.getlist('site2')

    reports2 = Report.objects.all()

    if year2:
        reports2 = reports2.filter(start_period__year__in=year2)
    if month2:
        reports2 = reports2.filter(start_period__month__in=month2)
    if segment2:
        reports2 = reports2.filter(segment__in=segment2)
    if site2:
        reports2 = reports2.filter(site__in=site2)

    years2 = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months2 = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                      flat=True).distinct().order_by(
        'month')
    segments2 = Report.objects.values_list('segment', flat=True).distinct()
    sites2 = Report.objects.values_list('site', flat=True).distinct()

    months2 = sorted([(m, MONTHS[m]) for m in months2 if m in MONTHS.keys()])

    avg_missed_profit_igore = 0
    count_missed_profit = 0
    for rep in reports:
        avg_missed_profit_igore += rep.missed_profit
        count_missed_profit += 1
    avg_missed_profit_igore = avg_missed_profit_igore / count_missed_profit

    avg_direct_losses_ignored = 0
    count_avg_direct_losses_ignored = 0
    for rep in reports:
        avg_direct_losses_ignored += rep.direct_losses_ignored
        count_avg_direct_losses_ignored += 1
    avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

    # Для периода 1
    # суммарные показатели

    total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                  'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals = reports.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                     'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
    avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                             2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
    roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                            2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                           2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                  2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                       2) if total_qualified_deals > 0 else None  # Общий Средний чек
    conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                        2) if total_leads > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                    2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                            2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                         2) if total_deals > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                 2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
        float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                          2) if total_deals > 0 else None  # Общий Упущенная прибыль

    # Средние показатели

    avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
    avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
    avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
    avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                'unqualified_leads__avg'] or 0  # Среднее некач. лидов
    avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
    avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                              'qualified_deals__avg'] or 0  # Среднее качественных сделок
    avg_failed_deals = reports.aggregate(Avg('failed_deals'))['failed_deals__avg'] or 0  # Среднее проваленных сделок
    avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                   'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
    avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

    # Для периода 2
    # суммарные показатели

    total_budget2 = reports2.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks2 = reports2.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads2 = reports2.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads2 = reports2.aggregate(Sum('unqualified_leads'))[
                                   'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals2 = reports2.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals2 = reports2.aggregate(Sum('qualified_deals'))[
                                 'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals2 = reports2.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals2 = reports2.aggregate(Sum('ignored_failed_deals'))[
                                      'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue2 = reports2.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead2 = round(total_budget2 / total_leads2, 2) if total_leads2 > 0 else None  # Общий CPA Лида
    avg_cpa_deal2 = round(total_budget2 / total_deals2, 2) if total_deals2 > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal2 = round(total_budget2 / total_qualified_deals2,
                              2) if total_deals2 > 0 else None  # Общий CPA Выигранной Сделки
    roi2 = round((total_revenue2 - total_budget2) / total_budget2 * 100, 2) if total_budget2 > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads2 = round((total_leads2 / total_clicks2 * 100),
                                             2) if total_clicks2 > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals2 = round((total_deals2 / total_leads2 * 100),
                                            2) if total_leads2 > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored2 = round(total_ignored_failed_deals2 * (avg_cpa_deal2 or 0),
                                   2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal2 = round(total_revenue2 / total_qualified_deals2,
                                        2) if total_qualified_deals2 > 0 else None  # Общий Средний чек
    conversion_rate_unqualified2 = round((total_unqualified_leads2 / total_leads2 * 100),
                                         2) if total_leads2 > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals2 = round((total_qualified_deals2 / total_leads2 * 100),
                                                     2) if total_deals2 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals2 = round((total_qualified_deals2 / total_deals2 * 100),
                                             2) if total_deals2 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals2 = round((total_failed_deals2 / total_deals2 * 100),
                                          2) if total_deals2 > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals2 = round((total_ignored_failed_deals2 / total_deals2 * 100),
                                                  2) if total_deals2 > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit2 = round(((total_ignored_failed_deals2 * conversion_rate_qualified_deals2 / 100) * (
        float(revenue_per_qualified_deal2) if revenue_per_qualified_deal2 is not None else 0)),
                           2) if total_deals2 > 0 else None  # Общий Упущенная прибыль

    context = {
        'title': 'Общие показатели за ' + str(month) + ' ' + str(year),

        # для периода 1
        'reports': reports,
        'years': years,
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        'total_budget': total_budget,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'total_unqualified_leads': total_unqualified_leads,
        'total_deals': total_deals,
        'total_qualified_deals': total_qualified_deals,
        'total_failed_deals': total_failed_deals,
        'total_ignored_failed_deals': total_ignored_failed_deals,
        'total_revenue': total_revenue,
        'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
        'avg_cpa_lead': avg_cpa_lead,
        'avg_cpa_deal': avg_cpa_deal,
        'avg_cpa_won_deal': avg_cpa_won_deal,
        'roi': roi,
        'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
        'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
        'direct_losses_ignored': direct_losses_ignored,
        'missed_profit': missed_profit,
        'revenue_per_qualified_deal': revenue_per_qualified_deal,
        'conversion_rate_unqualified': conversion_rate_unqualified,
        'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
        'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
        'conversion_rate_failed_deals': conversion_rate_failed_deals,
        'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
        # передаем средние
        'avg_budget': avg_budget,
        'avg_clicks': avg_clicks,
        'avg_leads': avg_leads,
        'avg_unqualified_leads': avg_unqualified_leads,
        'avg_deals': avg_deals,
        'avg_qualified_deals': avg_qualified_deals,
        'avg_failed_deals': avg_failed_deals,
        'avg_ignored_failed_deals': avg_ignored_failed_deals,
        'avg_revenue': avg_revenue,
        'avg_missed_profit_igore': avg_missed_profit_igore,
        # 'avg_direct_losses_ignored': avg_direct_losses_ignored,

        # для периода 2

        'reports2': reports2,
        'years2': years2,
        'months2': months2,
        'segments2': segments2,
        'sites2': sites2,
        'year2': year2,
        'month2': month2,
        'segment2': segment2,
        'site2': site2,
        'total_budget2': total_budget2,
        'total_clicks2': total_clicks2,
        'total_leads2': total_leads2,
        'total_unqualified_leads2': total_unqualified_leads2,
        'total_deals2': total_deals2,
        'total_qualified_deals2': total_qualified_deals2,
        'total_failed_deals2': total_failed_deals2,
        'total_ignored_failed_deals2': total_ignored_failed_deals2,
        'total_revenue2': total_revenue2,
        'average_conversion_rate2': f"{round((total_leads2 / total_clicks2) * 100, 2)}%" if total_clicks2 > 0 else "Н/Д",
        'avg_cpa_lead2': avg_cpa_lead2,
        'avg_cpa_deal2': avg_cpa_deal2,
        'avg_cpa_won_deal2': avg_cpa_won_deal2,
        'roi2': roi2,
        'conversion_rate_clicks_to_leads2': conversion_rate_clicks_to_leads2,
        'conversion_rate_leads_to_deals2': conversion_rate_leads_to_deals2,
        'direct_losses_ignored2': direct_losses_ignored2,
        'missed_profit2': missed_profit2,
        'revenue_per_qualified_deal2': revenue_per_qualified_deal2,
        'conversion_rate_unqualified2': conversion_rate_unqualified2,
        'conversion_rate_qualified_leds_to_deals2': conversion_rate_qualified_leds_to_deals2,
        'conversion_rate_qualified_deals2': conversion_rate_qualified_deals2,
        'conversion_rate_failed_deals2': conversion_rate_failed_deals2,
        'conversion_rate_ignored_failed_deals2': conversion_rate_ignored_failed_deals2,

        # Общие средние

        'avg_total_budget': (total_budget + total_budget2) / 2,
        'avg_total_clicks': (total_clicks + total_clicks2) / 2,
        'avg_total_leads': (total_leads + total_leads2) / 2,
        'avg_total_unqualified_leads': (total_unqualified_leads + total_unqualified_leads2) / 2,
        'avg_total_deals': (total_deals + total_deals2) / 2,
        'avg_total_qualified_deals': (total_qualified_deals + total_qualified_deals2) / 2,
        'avg_total_failed_deals': (total_failed_deals + total_failed_deals2) / 2,
        'avg_total_ignored_failed_deals': (total_ignored_failed_deals + total_ignored_failed_deals2) / 2,
        'avg_total_revenue': (total_revenue + total_revenue2) / 2,
        'avg_avg_cpa_lead': (avg_cpa_lead + avg_cpa_lead2) / 2,
        'avg_avg_cpa_deal': (avg_cpa_deal + avg_cpa_deal2) / 2,
        'avg_avg_cpa_won_deal': (avg_cpa_won_deal + avg_cpa_won_deal2) / 2,
        'avg_roi': (roi + roi2) / 2,
        'avg_conversion_rate_clicks_to_leads': (
                                                   conversion_rate_clicks_to_leads + conversion_rate_clicks_to_leads2) / 2,
        'avg_conversion_rate_leads_to_deals': (conversion_rate_leads_to_deals + conversion_rate_leads_to_deals2) / 2,
        'avg_direct_losses_ignored': (direct_losses_ignored + direct_losses_ignored2) / 2,
        'avg_missed_profit': (missed_profit + missed_profit2) / 2,
        'avg_revenue_per_qualified_deal': (revenue_per_qualified_deal + revenue_per_qualified_deal2) / 2,
        'avg_conversion_rate_unqualified': (conversion_rate_unqualified + conversion_rate_unqualified2) / 2,
        'avg_conversion_rate_qualified_leds_to_deals': (
                                                           conversion_rate_qualified_leds_to_deals + conversion_rate_qualified_leds_to_deals2) / 2,
        'avg_conversion_rate_qualified_deals': (
                                                   conversion_rate_qualified_deals + conversion_rate_qualified_deals2) / 2,
        'avg_conversion_rate_failed_deals': (conversion_rate_failed_deals + conversion_rate_failed_deals2) / 2,
        'avg_conversion_rate_ignored_failed_deals': (
                                                        conversion_rate_ignored_failed_deals + conversion_rate_ignored_failed_deals2) / 2,

        # Общяя сумма

        'sum_total_budget': total_budget + total_budget2,
        'sum_total_clicks': total_clicks + total_clicks2,
        'sum_total_leads': total_leads + total_leads2,
        'sum_total_unqualified_leads': total_unqualified_leads + total_unqualified_leads2,
        'sum_total_deals': total_deals + total_deals2,
        'sum_total_qualified_deals': total_qualified_deals + total_qualified_deals2,
        'sum_total_failed_deals': total_failed_deals + total_failed_deals2,
        'sum_total_ignored_failed_deals': total_ignored_failed_deals + total_ignored_failed_deals2,
        'sum_total_revenue': total_revenue + total_revenue2,
        'sum_avg_cpa_lead': avg_cpa_lead + avg_cpa_lead2,
        'sum_avg_cpa_deal': avg_cpa_deal + avg_cpa_deal2,
        'sum_avg_cpa_won_deal': avg_cpa_won_deal + avg_cpa_won_deal2,
        'sum_roi': roi + roi2,
        'sum_conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads + conversion_rate_clicks_to_leads2,
        'sum_conversion_rate_leads_to_deals': conversion_rate_leads_to_deals + conversion_rate_leads_to_deals2,
        'sum_direct_losses_ignored': direct_losses_ignored + direct_losses_ignored2,
        'sum_missed_profit': missed_profit + missed_profit2,
        'sum_revenue_per_qualified_deal': revenue_per_qualified_deal + revenue_per_qualified_deal2,
        'sum_conversion_rate_unqualified': conversion_rate_unqualified + conversion_rate_unqualified2,
        'sum_conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals + conversion_rate_qualified_leds_to_deals2,
        'sum_conversion_rate_qualified_deals': conversion_rate_qualified_deals + conversion_rate_qualified_deals2,
        'sum_conversion_rate_failed_deals': conversion_rate_failed_deals + conversion_rate_failed_deals2,
        'sum_conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals + conversion_rate_ignored_failed_deals2,

        # Изменения

        'rost_total_budget': round((total_budget2 - total_budget) / total_budget * 100, 2),
        'rost_total_clicks': round((total_clicks2 - total_clicks) / total_clicks * 100, 2),
        'rost_total_leads': round((total_leads2 - total_leads) / total_leads * 100, 2),
        'rost_total_unqualified_leads': round(
            (total_unqualified_leads2 - total_unqualified_leads) / total_unqualified_leads * 100, 2),
        'rost_total_deals': round((total_deals2 - total_deals) / total_deals * 100, 2),
        'rost_total_qualified_deals': round(
            (total_qualified_deals2 - total_qualified_deals) / total_qualified_deals * 100, 2),
        'rost_total_failed_deals': round((total_failed_deals2 - total_failed_deals) / total_failed_deals * 100, 2),
        'rost_total_ignored_failed_deals': round(
            (total_ignored_failed_deals2 - total_ignored_failed_deals) / total_ignored_failed_deals * 100, 2),
        'rost_total_revenue': round((total_revenue2 - total_revenue) / total_revenue * 100, 2),
        'rost_avg_cpa_lead': round((avg_cpa_lead2 - avg_cpa_lead) / avg_cpa_lead * 100, 2),
        'rost_avg_cpa_deal': round((avg_cpa_deal2 - avg_cpa_deal) / avg_cpa_deal * 100, 2),
        'rost_avg_cpa_won_deal': round((avg_cpa_won_deal2 - avg_cpa_won_deal) / avg_cpa_won_deal * 100, 2),
        'rost_roi': round((roi2 - roi) / roi * 100, 2),
        'rost_conversion_rate_clicks_to_leads': round((
                                                          conversion_rate_clicks_to_leads2 - conversion_rate_clicks_to_leads) / conversion_rate_clicks_to_leads * 100,
                                                      2),
        'rost_conversion_rate_leads_to_deals': round(
            (conversion_rate_leads_to_deals2 - conversion_rate_leads_to_deals) / conversion_rate_leads_to_deals * 100,
            2),
        'rost_direct_losses_ignored': round(
            (direct_losses_ignored2 - direct_losses_ignored) / direct_losses_ignored * 100, 2),
        'rost_missed_profit': round((missed_profit2 - missed_profit) / missed_profit * 100, 2),
        'rost_revenue_per_qualified_deal': round(
            (revenue_per_qualified_deal2 - revenue_per_qualified_deal) / revenue_per_qualified_deal * 100, 2),
        'rost_conversion_rate_unqualified': round(
            (conversion_rate_unqualified2 - conversion_rate_unqualified) / conversion_rate_unqualified * 100, 2),
        'rost_conversion_rate_qualified_leds_to_deals': round((
                                                                  conversion_rate_qualified_leds_to_deals2 - conversion_rate_qualified_leds_to_deals) / conversion_rate_qualified_leds_to_deals * 100,
                                                              2),
        'rost_conversion_rate_qualified_deals': round((
                                                          conversion_rate_qualified_deals2 - conversion_rate_qualified_deals) / conversion_rate_qualified_deals * 100,
                                                      2),
        'rost_conversion_rate_failed_deals': round(
            (conversion_rate_failed_deals2 - conversion_rate_failed_deals) / conversion_rate_failed_deals * 100, 2),
        'rost_conversion_rate_ignored_failed_deals': round((
                                                               conversion_rate_ignored_failed_deals2 - conversion_rate_ignored_failed_deals) / conversion_rate_ignored_failed_deals * 100,
                                                           2),
    }

    return render(request, 'dash/report_obsh.html', context)


def report_rus(request):
    year = request.GET.getlist('year')
    month = request.GET.getlist('month')
    segment = request.GET.getlist('segment')
    site = request.GET.getlist('site')

    reports = Report.objects.all()

    if year:
        reports = reports.filter(start_period__year__in=year)
    if month:
        reports = reports.filter(start_period__month__in=month)
    if segment:
        reports = reports.filter(segment__in=segment)
    if site:
        reports = reports.filter(site__in=site)

    years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                     flat=True).distinct().order_by(
        'month')
    segments = Report.objects.values_list('segment', flat=True).distinct()
    sites = Report.objects.values_list('site', flat=True).distinct()

    months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

    year2 = request.GET.getlist('year2')
    month2 = request.GET.getlist('month2')
    segment2 = request.GET.getlist('segment2')
    site2 = request.GET.getlist('site2')

    reports2 = Report.objects.all()

    if year2:
        reports2 = reports2.filter(start_period__year__in=year2)
    if month2:
        reports2 = reports2.filter(start_period__month__in=month2)
    if segment2:
        reports2 = reports2.filter(segment__in=segment2)
    if site2:
        reports2 = reports2.filter(site__in=site2)

    years2 = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
    months2 = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                      flat=True).distinct().order_by(
        'month')
    segments2 = Report.objects.values_list('segment', flat=True).distinct()
    sites2 = Report.objects.values_list('site', flat=True).distinct()

    months2 = sorted([(m, MONTHS[m]) for m in months2 if m in MONTHS.keys()])

    avg_missed_profit_igore = 0
    count_missed_profit = 0
    for rep in reports:
        avg_missed_profit_igore += rep.missed_profit
        count_missed_profit += 1
    avg_missed_profit_igore = avg_missed_profit_igore / count_missed_profit

    avg_direct_losses_ignored = 0
    count_avg_direct_losses_ignored = 0
    for rep in reports:
        avg_direct_losses_ignored += rep.direct_losses_ignored
        count_avg_direct_losses_ignored += 1
    avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

    # Для периода 1
    # суммарные показатели

    total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                  'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals = reports.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                     'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
    avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                             2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
    roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                            2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                           2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                  2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                       2) if total_qualified_deals > 0 else None  # Общий Средний чек
    conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                        2) if total_leads > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                    2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                            2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                         2) if total_deals > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                 2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
        float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                          2) if total_deals > 0 else None  # Общий Упущенная прибыль

    # Средние показатели

    avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
    avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
    avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
    avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                'unqualified_leads__avg'] or 0  # Среднее некач. лидов
    avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
    avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                              'qualified_deals__avg'] or 0  # Среднее качественных сделок
    avg_failed_deals = reports.aggregate(Avg('failed_deals'))['failed_deals__avg'] or 0  # Среднее проваленных сделок
    avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                   'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
    avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

    # Для периода 2
    # суммарные показатели

    total_budget2 = reports2.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
    total_clicks2 = reports2.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
    total_leads2 = reports2.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
    total_unqualified_leads2 = reports2.aggregate(Sum('unqualified_leads'))[
                                   'unqualified_leads__sum'] or 0  # Сумма некач. лидов
    total_deals2 = reports2.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
    total_qualified_deals2 = reports2.aggregate(Sum('qualified_deals'))[
                                 'qualified_deals__sum'] or 0  # Сумма качественных сделок
    total_failed_deals2 = reports2.aggregate(Sum('failed_deals'))['failed_deals__sum'] or 0  # Сумма проваленных сделок
    total_ignored_failed_deals2 = reports2.aggregate(Sum('ignored_failed_deals'))[
                                      'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
    total_revenue2 = reports2.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead2 = round(total_budget2 / total_leads2, 2) if total_leads2 > 0 else None  # Общий CPA Лида
    avg_cpa_deal2 = round(total_budget2 / total_deals2, 2) if total_deals2 > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal2 = round(total_budget2 / total_qualified_deals2,
                              2) if total_deals2 > 0 else None  # Общий CPA Выигранной Сделки
    roi2 = round((total_revenue2 - total_budget2) / total_budget2 * 100, 2) if total_budget2 > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads2 = round((total_leads2 / total_clicks2 * 100),
                                             2) if total_clicks2 > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals2 = round((total_deals2 / total_leads2 * 100),
                                            2) if total_leads2 > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored2 = round(total_ignored_failed_deals2 * (avg_cpa_deal2 or 0),
                                   2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal2 = round(total_revenue2 / total_qualified_deals2,
                                        2) if total_qualified_deals2 > 0 else None  # Общий Средний чек
    conversion_rate_unqualified2 = round((total_unqualified_leads2 / total_leads2 * 100),
                                         2) if total_leads2 > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals2 = round((total_qualified_deals2 / total_leads2 * 100),
                                                     2) if total_deals2 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals2 = round((total_qualified_deals2 / total_deals2 * 100),
                                             2) if total_deals2 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals2 = round((total_failed_deals2 / total_deals2 * 100),
                                          2) if total_deals2 > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals2 = round((total_ignored_failed_deals2 / total_deals2 * 100),
                                                  2) if total_deals2 > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit2 = round(((total_ignored_failed_deals2 * conversion_rate_qualified_deals2 / 100) * (
        float(revenue_per_qualified_deal2) if revenue_per_qualified_deal2 is not None else 0)),
                           2) if total_deals2 > 0 else None  # Общий Упущенная прибыль

    # Для суммарного периода
    # суммарные показатели

    total_budget3 = total_budget + total_budget2
    total_clicks3 = total_clicks + total_clicks2  # Сумма кликов
    total_leads3 = total_leads + total_leads2
    total_unqualified_leads3 = total_unqualified_leads + total_unqualified_leads2  # Сумма некач. лидов
    total_deals3 = total_deals + total_deals2  # Сумма качественных сделок
    total_qualified_deals3 = total_qualified_deals + total_qualified_deals2  # Сумма качественных сделок
    total_failed_deals3 = total_failed_deals + total_failed_deals2  # Сумма проваленных сделок
    total_ignored_failed_deals3 = total_ignored_failed_deals + total_ignored_failed_deals2  # Сумма некач. сделок игнор
    total_revenue3 = total_revenue + total_revenue2  # Сумма выручки

    # Вычисления для отображения
    avg_cpa_lead3 = round(total_budget3 / total_leads3, 2) if total_leads3 > 0 else None  # Общий CPA Лида
    avg_cpa_deal3 = round(total_budget3 / total_deals3, 2) if total_deals3 > 0 else None  # Общий CPA Сделки
    avg_cpa_won_deal3 = round(total_budget3 / total_qualified_deals3,
                              2) if total_deals3 > 0 else None  # Общий CPA Выигранной Сделки
    roi3 = round((total_revenue3 - total_budget3) / total_budget3 * 100, 2) if total_budget3 > 0 else None  # Общий РОЙ
    conversion_rate_clicks_to_leads3 = round((total_leads3 / total_clicks3 * 100),
                                             2) if total_clicks3 > 0 else None  # Общий CR% Кликов в Лиды
    conversion_rate_leads_to_deals3 = round((total_deals3 / total_leads3 * 100),
                                            2) if total_leads3 > 0 else None  # Общий CR% Лидов в Сделки
    direct_losses_ignored3 = round(total_ignored_failed_deals3 * (avg_cpa_deal3 or 0),
                                   2)  # Общий Потери прямые по причине игнора дел

    # Добавим дополнительные значения для шаблона с округлением
    revenue_per_qualified_deal3 = round(total_revenue3 / total_qualified_deals3,
                                        2) if total_qualified_deals3 > 0 else None  # Общий Средний чек
    conversion_rate_unqualified3 = round((total_unqualified_leads3 / total_leads3 * 100),
                                         2) if total_leads3 > 0 else None  # Общий CR% некач. Лидов
    conversion_rate_qualified_leds_to_deals3 = round((total_qualified_deals3 / total_leads3 * 100),
                                                     2) if total_deals3 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    conversion_rate_qualified_deals3 = round((total_qualified_deals3 / total_deals3 * 100),
                                             2) if total_deals3 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    conversion_rate_failed_deals3 = round((total_failed_deals3 / total_deals3 * 100),
                                          2) if total_deals3 > 0 else None  # Общий % провала Сделок
    conversion_rate_ignored_failed_deals3 = round((total_ignored_failed_deals3 / total_deals3 * 100),
                                                  2) if total_deals3 > 0 else None  # Общий % провала Сделок по причине игнор дел

    missed_profit3 = round(((total_ignored_failed_deals3 * conversion_rate_qualified_deals3 / 100) * (
        float(revenue_per_qualified_deal3) if revenue_per_qualified_deal3 is not None else 0)),
                           2) if total_deals3 > 0 else None  # Общий Упущенная прибыль

    # Средние показатели

    avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
    avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
    avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
    avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                'unqualified_leads__avg'] or 0  # Среднее некач. лидов
    avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
    avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                              'qualified_deals__avg'] or 0  # Среднее качественных сделок
    avg_failed_deals = reports.aggregate(Avg('failed_deals'))['failed_deals__avg'] or 0  # Среднее проваленных сделок
    avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                   'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
    avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

    context = {
        'title': 'Отчет сравнение периодов ' + str(month) + ' ' + str(year) + ' ' + str(month2) + ' ' + str(year2),

        # для периода 1
        'reports': reports,
        'years': years,
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        'total_budget': total_budget,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'total_unqualified_leads': total_unqualified_leads,
        'total_deals': total_deals,
        'total_qualified_deals': total_qualified_deals,
        'total_failed_deals': total_failed_deals,
        'total_ignored_failed_deals': total_ignored_failed_deals,
        'total_revenue': total_revenue,
        'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
        'avg_cpa_lead': avg_cpa_lead,
        'avg_cpa_deal': avg_cpa_deal,
        'avg_cpa_won_deal': avg_cpa_won_deal,
        'roi': roi,
        'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
        'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
        'direct_losses_ignored': direct_losses_ignored,
        'missed_profit': missed_profit,
        'revenue_per_qualified_deal': revenue_per_qualified_deal,
        'conversion_rate_unqualified': conversion_rate_unqualified,
        'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
        'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
        'conversion_rate_failed_deals': conversion_rate_failed_deals,
        'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
        # передаем средние
        'avg_budget': avg_budget,
        'avg_clicks': avg_clicks,
        'avg_leads': avg_leads,
        'avg_unqualified_leads': avg_unqualified_leads,
        'avg_deals': avg_deals,
        'avg_qualified_deals': avg_qualified_deals,
        'avg_failed_deals': avg_failed_deals,
        'avg_ignored_failed_deals': avg_ignored_failed_deals,
        'avg_revenue': avg_revenue,
        'avg_missed_profit_igore': avg_missed_profit_igore,
        # 'avg_direct_losses_ignored': avg_direct_losses_ignored,

        # для периода 2

        'reports2': reports2,
        'years2': years2,
        'months2': months2,
        'segments2': segments2,
        'sites2': sites2,
        'year2': year2,
        'month2': month2,
        'segment2': segment2,
        'site2': site2,
        'total_budget2': total_budget2,
        'total_clicks2': total_clicks2,
        'total_leads2': total_leads2,
        'total_unqualified_leads2': total_unqualified_leads2,
        'total_deals2': total_deals2,
        'total_qualified_deals2': total_qualified_deals2,
        'total_failed_deals2': total_failed_deals2,
        'total_ignored_failed_deals2': total_ignored_failed_deals2,
        'total_revenue2': total_revenue2,
        'average_conversion_rate2': f"{round((total_leads2 / total_clicks2) * 100, 2)}%" if total_clicks2 > 0 else "Н/Д",
        'avg_cpa_lead2': avg_cpa_lead2,
        'avg_cpa_deal2': avg_cpa_deal2,
        'avg_cpa_won_deal2': avg_cpa_won_deal2,
        'roi2': roi2,
        'conversion_rate_clicks_to_leads2': conversion_rate_clicks_to_leads2,
        'conversion_rate_leads_to_deals2': conversion_rate_leads_to_deals2,
        'direct_losses_ignored2': direct_losses_ignored2,
        'missed_profit2': missed_profit2,
        'revenue_per_qualified_deal2': revenue_per_qualified_deal2,
        'conversion_rate_unqualified2': conversion_rate_unqualified2,
        'conversion_rate_qualified_leds_to_deals2': conversion_rate_qualified_leds_to_deals2,
        'conversion_rate_qualified_deals2': conversion_rate_qualified_deals2,
        'conversion_rate_failed_deals2': conversion_rate_failed_deals2,
        'conversion_rate_ignored_failed_deals2': conversion_rate_ignored_failed_deals2,

        # Общие средние

        'avg_total_budget': (total_budget + total_budget2) / 2,
        'avg_total_clicks': (total_clicks + total_clicks2) / 2,
        'avg_total_leads': (total_leads + total_leads2) / 2,
        'avg_total_unqualified_leads': (total_unqualified_leads + total_unqualified_leads2) / 2,
        'avg_total_deals': (total_deals + total_deals2) / 2,
        'avg_total_qualified_deals': (total_qualified_deals + total_qualified_deals2) / 2,
        'avg_total_failed_deals': (total_failed_deals + total_failed_deals2) / 2,
        'avg_total_ignored_failed_deals': (total_ignored_failed_deals + total_ignored_failed_deals2) / 2,
        'avg_total_revenue': (total_revenue + total_revenue2) / 2,
        'avg_avg_cpa_lead': (avg_cpa_lead + avg_cpa_lead2) / 2,
        'avg_avg_cpa_deal': (avg_cpa_deal + avg_cpa_deal2) / 2,
        'avg_avg_cpa_won_deal': (avg_cpa_won_deal + avg_cpa_won_deal2) / 2,
        'avg_roi': (roi + roi2) / 2,
        'avg_conversion_rate_clicks_to_leads': (
                                                   conversion_rate_clicks_to_leads + conversion_rate_clicks_to_leads2) / 2,
        'avg_conversion_rate_leads_to_deals': (conversion_rate_leads_to_deals + conversion_rate_leads_to_deals2) / 2,
        'avg_direct_losses_ignored': (direct_losses_ignored + direct_losses_ignored2) / 2,
        'avg_missed_profit': (missed_profit + missed_profit2) / 2,
        'avg_revenue_per_qualified_deal': (revenue_per_qualified_deal + revenue_per_qualified_deal2) / 2,
        'avg_conversion_rate_unqualified': (conversion_rate_unqualified + conversion_rate_unqualified2) / 2,
        'avg_conversion_rate_qualified_leds_to_deals': (
                                                           conversion_rate_qualified_leds_to_deals + conversion_rate_qualified_leds_to_deals2) / 2,
        'avg_conversion_rate_qualified_deals': (
                                                   conversion_rate_qualified_deals + conversion_rate_qualified_deals2) / 2,
        'avg_conversion_rate_failed_deals': (conversion_rate_failed_deals + conversion_rate_failed_deals2) / 2,
        'avg_conversion_rate_ignored_failed_deals': (
                                                        conversion_rate_ignored_failed_deals + conversion_rate_ignored_failed_deals2) / 2,

        # Общяя сумма

        'sum_total_budget': total_budget + total_budget2,
        'sum_total_clicks': total_clicks + total_clicks2,
        'sum_total_leads': total_leads + total_leads2,
        'sum_total_unqualified_leads': total_unqualified_leads + total_unqualified_leads2,
        'sum_total_deals': total_deals + total_deals2,
        'sum_total_qualified_deals': total_qualified_deals + total_qualified_deals2,
        'sum_total_failed_deals': total_failed_deals + total_failed_deals2,
        'sum_total_ignored_failed_deals': total_ignored_failed_deals3,
        'sum_total_revenue': total_revenue + total_revenue2,
        'sum_avg_cpa_lead': avg_cpa_lead3,
        'sum_avg_cpa_deal': avg_cpa_deal3,
        'sum_avg_cpa_won_deal': avg_cpa_won_deal3,
        'sum_roi': roi3,

        'sum_conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads3,
        'sum_conversion_rate_leads_to_deals': conversion_rate_leads_to_deals3,
        'sum_direct_losses_ignored': direct_losses_ignored + direct_losses_ignored2,
        'sum_missed_profit': missed_profit + missed_profit2,
        'sum_revenue_per_qualified_deal': revenue_per_qualified_deal3,
        'sum_conversion_rate_unqualified': conversion_rate_unqualified3,
        'sum_conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals3,
        'sum_conversion_rate_qualified_deals': conversion_rate_qualified_deals3,
        'sum_conversion_rate_failed_deals': conversion_rate_failed_deals3,
        'sum_conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals3,

        # Изменения

        'rost_total_budget': round((total_budget2 - total_budget) / total_budget * 100, 2),
        'rost_total_clicks': round((total_clicks2 - total_clicks) / total_clicks * 100, 2),
        'rost_total_leads': round((total_leads2 - total_leads) / total_leads * 100, 2),
        'rost_total_unqualified_leads': round(
            (total_unqualified_leads2 - total_unqualified_leads) / total_unqualified_leads * 100, 2),
        'rost_total_deals': round((total_deals2 - total_deals) / total_deals * 100, 2),
        'rost_total_qualified_deals': round(
            (total_qualified_deals2 - total_qualified_deals) / total_qualified_deals * 100, 2),
        'rost_total_failed_deals': round((total_failed_deals2 - total_failed_deals) / total_failed_deals * 100, 2),
        'rost_total_ignored_failed_deals': round(
            (total_ignored_failed_deals2 - total_ignored_failed_deals) / total_ignored_failed_deals * 100, 2),
        'rost_total_revenue': round((total_revenue2 - total_revenue) / total_revenue * 100, 2),
        'rost_avg_cpa_lead': round((avg_cpa_lead2 - avg_cpa_lead) / avg_cpa_lead * 100, 2),
        'rost_avg_cpa_deal': round((avg_cpa_deal2 - avg_cpa_deal) / avg_cpa_deal * 100, 2),
        'rost_avg_cpa_won_deal': round((avg_cpa_won_deal2 - avg_cpa_won_deal) / avg_cpa_won_deal * 100, 2),
        'rost_roi': round((roi2 - roi) / roi * 100, 2),
        'rost_conversion_rate_clicks_to_leads': round((
                                                          conversion_rate_clicks_to_leads2 - conversion_rate_clicks_to_leads) / conversion_rate_clicks_to_leads * 100,
                                                      2),
        'rost_conversion_rate_leads_to_deals': round(
            (conversion_rate_leads_to_deals2 - conversion_rate_leads_to_deals) / conversion_rate_leads_to_deals * 100,
            2),
        'rost_direct_losses_ignored': round(
            (direct_losses_ignored2 - direct_losses_ignored) / direct_losses_ignored * 100, 2),
        'rost_missed_profit': round((missed_profit2 - missed_profit) / missed_profit * 100, 2),
        'rost_revenue_per_qualified_deal': round(
            (revenue_per_qualified_deal2 - revenue_per_qualified_deal) / revenue_per_qualified_deal * 100, 2),
        'rost_conversion_rate_unqualified': round(
            (conversion_rate_unqualified2 - conversion_rate_unqualified) / conversion_rate_unqualified * 100, 2),
        'rost_conversion_rate_qualified_leds_to_deals': round((
                                                                  conversion_rate_qualified_leds_to_deals2 - conversion_rate_qualified_leds_to_deals) / conversion_rate_qualified_leds_to_deals * 100,
                                                              2),
        'rost_conversion_rate_qualified_deals': round((
                                                          conversion_rate_qualified_deals2 - conversion_rate_qualified_deals) / conversion_rate_qualified_deals * 100,
                                                      2),
        'rost_conversion_rate_failed_deals': round(
            (conversion_rate_failed_deals2 - conversion_rate_failed_deals) / conversion_rate_failed_deals * 100, 2),
        'rost_conversion_rate_ignored_failed_deals': round((
                                                               conversion_rate_ignored_failed_deals2 - conversion_rate_ignored_failed_deals) / conversion_rate_ignored_failed_deals * 100,
                                                           2),
    }

    return render(request, 'dash/report_rus.html', context)


class dashtestView(TemplateView):
    reports = Report.objects.all()
    shipment = [20, 45, 33, 38, 32, 50, 48, 40, 42, 37]
    delivery = [23, 28, 23, 32, 28, 44, 32, 38, 26, 34]

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['reports'] = self.reports
        context['shipment'] = self.shipment
        context['delivery'] = self.delivery

        return context


class ReportList(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year = self.request.GET.getlist('year')
        month = self.request.GET.getlist('month')
        segment = self.request.GET.getlist('segment')
        site = self.request.GET.getlist('site')

        reports = Report.objects.all()

        if year:
            reports = reports.filter(start_period__year__in=year)
        if month:
            reports = reports.filter(start_period__month__in=month)
        if segment:
            reports = reports.filter(segment__in=segment)
        if site:
            reports = reports.filter(site__in=site)

        years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                         flat=True).distinct().order_by(
            'month')
        segments = Report.objects.values_list('segment', flat=True).distinct()
        sites = Report.objects.values_list('site', flat=True).distinct()

        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

        total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                      'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                    'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals = reports.aggregate(Sum('failed_deals'))[
                                 'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                         'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
        avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                                 2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
        roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                                2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                               2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                      2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                           2) if total_qualified_deals > 0 else None  # Общий Средний чек
        conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                            2) if total_leads > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                        2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                                2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                             2) if total_deals > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                     2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
            float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                              2) if total_deals > 0 else None  # Общий Упущенная прибыль

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
            'total_budget': total_budget,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'total_unqualified_leads': total_unqualified_leads,
            'total_deals': total_deals,
            'total_qualified_deals': total_qualified_deals,
            'total_failed_deals': total_failed_deals,
            'total_ignored_failed_deals': total_ignored_failed_deals,
            'total_revenue': total_revenue,
            'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
            'avg_cpa_lead': avg_cpa_lead,
            'avg_cpa_deal': avg_cpa_deal,
            'avg_cpa_won_deal': avg_cpa_won_deal,
            'roi': roi,
            'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
            'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
            'direct_losses_ignored': direct_losses_ignored,
            'missed_profit': missed_profit,
            'revenue_per_qualified_deal': revenue_per_qualified_deal,
            'conversion_rate_unqualified': conversion_rate_unqualified,
            'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
            'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
            'conversion_rate_failed_deals': conversion_rate_failed_deals,
            'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
        })

        return context


class ReportMonth(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year = self.request.GET.getlist('year')
        month = self.request.GET.getlist('month')
        segment = self.request.GET.getlist('segment')
        site = self.request.GET.getlist('site')

        reports = Report.objects.all()

        if year:
            reports = reports.filter(start_period__year__in=year)
        if month:
            reports = reports.filter(start_period__month__in=month)
        if segment:
            reports = reports.filter(segment__in=segment)
        if site:
            reports = reports.filter(site__in=site)

        years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                         flat=True).distinct().order_by(
            'month')
        segments = Report.objects.values_list('segment', flat=True).distinct()
        sites = Report.objects.values_list('site', flat=True).distinct()

        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

        total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                      'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                    'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals = reports.aggregate(Sum('failed_deals'))[
                                 'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                         'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
        avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                                 2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
        roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                                2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                               2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                      2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                           2) if total_qualified_deals > 0 else None  # Общий Средний чек
        conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                            2) if total_leads > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                        2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                                2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                             2) if total_deals > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                     2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
            float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                              2) if total_deals > 0 else None  # Общий Упущенная прибыль

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
            'total_budget': total_budget,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'total_unqualified_leads': total_unqualified_leads,
            'total_deals': total_deals,
            'total_qualified_deals': total_qualified_deals,
            'total_failed_deals': total_failed_deals,
            'total_ignored_failed_deals': total_ignored_failed_deals,
            'total_revenue': total_revenue,
            'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
            'avg_cpa_lead': avg_cpa_lead,
            'avg_cpa_deal': avg_cpa_deal,
            'avg_cpa_won_deal': avg_cpa_won_deal,
            'roi': roi,
            'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
            'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
            'direct_losses_ignored': direct_losses_ignored,
            'missed_profit': missed_profit,
            'revenue_per_qualified_deal': revenue_per_qualified_deal,
            'conversion_rate_unqualified': conversion_rate_unqualified,
            'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
            'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
            'conversion_rate_failed_deals': conversion_rate_failed_deals,
            'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
        })

        return context


class ReportSegSite(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year = self.request.GET.getlist('year')
        month = self.request.GET.getlist('month')
        segment = self.request.GET.getlist('segment')
        site = self.request.GET.getlist('site')

        reports = Report.objects.all()

        if year:
            reports = reports.filter(start_period__year__in=year)
        if month:
            reports = reports.filter(start_period__month__in=month)
        if segment:
            reports = reports.filter(segment__in=segment)
        if site:
            reports = reports.filter(site__in=site)

        years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                         flat=True).distinct().order_by(
            'month')
        segments = Report.objects.values_list('segment', flat=True).distinct()
        sites = Report.objects.values_list('site', flat=True).distinct()

        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

        avg_missed_profit_igore = 0
        count_missed_profit = 0
        for rep in reports:
            avg_missed_profit_igore += rep.missed_profit
            count_missed_profit += 1
        avg_missed_profit_igore = round(avg_missed_profit_igore / count_missed_profit, 2)

        avg_direct_losses_ignored = 0
        count_avg_direct_losses_ignored = 0
        for rep in reports:
            avg_direct_losses_ignored += rep.direct_losses_ignored
            count_avg_direct_losses_ignored += 1
        avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

        # суммарные показатели

        total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or None  # Сумма лидов
        total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                      'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                    'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals = reports.aggregate(Sum('failed_deals'))[
                                 'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                         'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else 0  # Общий CPA Лида
        avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else 0  # Общий CPA Сделки
        avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                                 2) if total_deals > 0 else 0  # Общий CPA Выигранной Сделки
        roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                                2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                               2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                      2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                           2) if total_qualified_deals > 0 else None  # Общий Средний чек
        conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                            2) if total_leads > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                        2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                                2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                             2) if total_deals > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                     2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
            float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                              2) if total_deals > 0 else None  # Общий Упущенная прибыль

        # Средние показатели

        avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
        avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
        avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
        avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                    'unqualified_leads__avg'] or 0  # Среднее некач. лидов
        avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
        avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                                  'qualified_deals__avg'] or 0  # Среднее качественных сделок
        avg_failed_deals = reports.aggregate(Avg('failed_deals'))[
                               'failed_deals__avg'] or 0  # Среднее проваленных сделок
        avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                       'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
        avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

        context.update({
            'title': 'Отчет по сегментам и сайтам ' + str(month) + ' ' + str(year),
            'reports': reports,
            'years': years,
            'months': months,
            'segments': segments,
            'sites': sites,
            'year': year,
            'month': month,
            'segment': segment,
            'site': site,
            'total_budget': total_budget,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'total_unqualified_leads': total_unqualified_leads,
            'total_deals': total_deals,
            'total_qualified_deals': total_qualified_deals,
            'total_failed_deals': total_failed_deals,
            'total_ignored_failed_deals': total_ignored_failed_deals,
            'total_revenue': total_revenue,
            'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
            'avg_cpa_lead': avg_cpa_lead,
            'avg_cpa_deal': avg_cpa_deal,
            'avg_cpa_won_deal': avg_cpa_won_deal,
            'roi': roi,
            'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
            'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
            'direct_losses_ignored': direct_losses_ignored,
            'missed_profit': missed_profit,
            'revenue_per_qualified_deal': revenue_per_qualified_deal,
            'conversion_rate_unqualified': conversion_rate_unqualified,
            'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
            'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
            'conversion_rate_failed_deals': conversion_rate_failed_deals,
            'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
            # передаем средние
            'avg_budget': round(avg_budget, 2),
            'avg_clicks': round(avg_clicks, 2),
            'avg_leads': round(avg_leads, 2),
            'avg_unqualified_leads': round(avg_unqualified_leads, 2),
            'avg_deals': round(avg_deals, 2),
            'avg_qualified_deals': round(avg_qualified_deals, 2),
            'avg_failed_deals': round(avg_failed_deals, 2),
            'avg_ignored_failed_deals': round(avg_ignored_failed_deals, 2),
            'avg_revenue': round(avg_revenue, 2),
            'avg_missed_profit_igore': round(avg_missed_profit_igore, 2),
            'avg_direct_losses_ignored': round(avg_direct_losses_ignored, 2),
        })

        return context


class ReportSrav(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year = self.request.GET.getlist('year')
        month = self.request.GET.getlist('month')
        segment = self.request.GET.getlist('segment')
        site = self.request.GET.getlist('site')

        reports = Report.objects.all()

        if year:
            reports = reports.filter(start_period__year__in=year)
        if month:
            reports = reports.filter(start_period__month__in=month)
        if segment:
            reports = reports.filter(segment__in=segment)
        if site:
            reports = reports.filter(site__in=site)

        years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                         flat=True).distinct().order_by(
            'month')
        segments = Report.objects.values_list('segment', flat=True).distinct()
        sites = Report.objects.values_list('site', flat=True).distinct()

        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

        year2 = self.request.GET.getlist('year2')
        month2 = self.request.GET.getlist('month2')
        segment2 = self.request.GET.getlist('segment2')
        site2 = self.request.GET.getlist('site2')

        reports2 = Report.objects.all()

        if year2:
            reports2 = reports2.filter(start_period__year__in=year2)
        if month2:
            reports2 = reports2.filter(start_period__month__in=month2)
        if segment2:
            reports2 = reports2.filter(segment__in=segment2)
        if site2:
            reports2 = reports2.filter(site__in=site2)

        years2 = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months2 = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                          flat=True).distinct().order_by(
            'month')
        segments2 = Report.objects.values_list('segment', flat=True).distinct()
        sites2 = Report.objects.values_list('site', flat=True).distinct()

        months2 = sorted([(m, MONTHS[m]) for m in months2 if m in MONTHS.keys()])

        avg_missed_profit_igore = 0
        count_missed_profit = 0
        for rep in reports:
            avg_missed_profit_igore += rep.missed_profit
            count_missed_profit += 1
        avg_missed_profit_igore = avg_missed_profit_igore / count_missed_profit

        avg_direct_losses_ignored = 0
        count_avg_direct_losses_ignored = 0
        for rep in reports:
            avg_direct_losses_ignored += rep.direct_losses_ignored
            count_avg_direct_losses_ignored += 1
        avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

        # Для периода 1
        # суммарные показатели

        total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                      'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                    'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals = reports.aggregate(Sum('failed_deals'))[
                                 'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                         'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
        avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                                 2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
        roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                                2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                               2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                      2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                           2) if total_qualified_deals > 0 else None  # Общий Средний чек
        conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                            2) if total_leads > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                        2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                                2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                             2) if total_deals > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                     2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
            float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                              2) if total_deals > 0 else None  # Общий Упущенная прибыль

        # Средние показатели

        avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
        avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
        avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
        avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                    'unqualified_leads__avg'] or 0  # Среднее некач. лидов
        avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
        avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                                  'qualified_deals__avg'] or 0  # Среднее качественных сделок
        avg_failed_deals = reports.aggregate(Avg('failed_deals'))[
                               'failed_deals__avg'] or 0  # Среднее проваленных сделок
        avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                       'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
        avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

        # Для периода 2
        # суммарные показатели

        total_budget2 = reports2.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks2 = reports2.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads2 = reports2.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads2 = reports2.aggregate(Sum('unqualified_leads'))[
                                       'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals2 = reports2.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals2 = reports2.aggregate(Sum('qualified_deals'))[
                                     'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals2 = reports2.aggregate(Sum('failed_deals'))[
                                  'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals2 = reports2.aggregate(Sum('ignored_failed_deals'))[
                                          'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue2 = reports2.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead2 = round(total_budget2 / total_leads2, 2) if total_leads2 > 0 else None  # Общий CPA Лида
        avg_cpa_deal2 = round(total_budget2 / total_deals2, 2) if total_deals2 > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal2 = round(total_budget2 / total_qualified_deals2,
                                  2) if total_deals2 > 0 else None  # Общий CPA Выигранной Сделки
        roi2 = round((total_revenue2 - total_budget2) / total_budget2 * 100,
                     2) if total_budget2 > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads2 = round((total_leads2 / total_clicks2 * 100),
                                                 2) if total_clicks2 > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals2 = round((total_deals2 / total_leads2 * 100),
                                                2) if total_leads2 > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored2 = round(total_ignored_failed_deals2 * (avg_cpa_deal2 or 0),
                                       2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal2 = round(total_revenue2 / total_qualified_deals2,
                                            2) if total_qualified_deals2 > 0 else None  # Общий Средний чек
        conversion_rate_unqualified2 = round((total_unqualified_leads2 / total_leads2 * 100),
                                             2) if total_leads2 > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals2 = round((total_qualified_deals2 / total_leads2 * 100),
                                                         2) if total_deals2 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals2 = round((total_qualified_deals2 / total_deals2 * 100),
                                                 2) if total_deals2 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals2 = round((total_failed_deals2 / total_deals2 * 100),
                                              2) if total_deals2 > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals2 = round((total_ignored_failed_deals2 / total_deals2 * 100),
                                                      2) if total_deals2 > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit2 = round(((total_ignored_failed_deals2 * conversion_rate_qualified_deals2 / 100) * (
            float(revenue_per_qualified_deal2) if revenue_per_qualified_deal2 is not None else 0)),
                               2) if total_deals2 > 0 else None  # Общий Упущенная прибыль

        # Для суммарного периода
        # суммарные показатели

        total_budget3 = total_budget + total_budget2
        total_clicks3 = total_clicks + total_clicks2  # Сумма кликов
        total_leads3 = total_leads + total_leads2
        total_unqualified_leads3 = total_unqualified_leads + total_unqualified_leads2  # Сумма некач. лидов
        total_deals3 = total_deals + total_deals2  # Сумма качественных сделок
        total_qualified_deals3 = total_qualified_deals + total_qualified_deals2  # Сумма качественных сделок
        total_failed_deals3 = total_failed_deals + total_failed_deals2  # Сумма проваленных сделок
        total_ignored_failed_deals3 = total_ignored_failed_deals + total_ignored_failed_deals2  # Сумма некач. сделок игнор
        total_revenue3 = total_revenue + total_revenue2  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead3 = round(total_budget3 / total_leads3, 2) if total_leads3 > 0 else None  # Общий CPA Лида
        avg_cpa_deal3 = round(total_budget3 / total_deals3, 2) if total_deals3 > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal3 = round(total_budget3 / total_qualified_deals3,
                                  2) if total_deals3 > 0 else None  # Общий CPA Выигранной Сделки
        roi3 = round((total_revenue3 - total_budget3) / total_budget3 * 100,
                     2) if total_budget3 > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads3 = round((total_leads3 / total_clicks3 * 100),
                                                 2) if total_clicks3 > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals3 = round((total_deals3 / total_leads3 * 100),
                                                2) if total_leads3 > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored3 = round(total_ignored_failed_deals3 * (avg_cpa_deal3 or 0),
                                       2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal3 = round(total_revenue3 / total_qualified_deals3,
                                            2) if total_qualified_deals3 > 0 else None  # Общий Средний чек
        conversion_rate_unqualified3 = round((total_unqualified_leads3 / total_leads3 * 100),
                                             2) if total_leads3 > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals3 = round((total_qualified_deals3 / total_leads3 * 100),
                                                         2) if total_deals3 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals3 = round((total_qualified_deals3 / total_deals3 * 100),
                                                 2) if total_deals3 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals3 = round((total_failed_deals3 / total_deals3 * 100),
                                              2) if total_deals3 > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals3 = round((total_ignored_failed_deals3 / total_deals3 * 100),
                                                      2) if total_deals3 > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit3 = round(((total_ignored_failed_deals3 * conversion_rate_qualified_deals3 / 100) * (
            float(revenue_per_qualified_deal3) if revenue_per_qualified_deal3 is not None else 0)),
                               2) if total_deals3 > 0 else None  # Общий Упущенная прибыль

        # Средние показатели

        avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
        avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
        avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
        avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                    'unqualified_leads__avg'] or 0  # Среднее некач. лидов
        avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
        avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                                  'qualified_deals__avg'] or 0  # Среднее качественных сделок
        avg_failed_deals = reports.aggregate(Avg('failed_deals'))[
                               'failed_deals__avg'] or 0  # Среднее проваленных сделок
        avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                       'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
        avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

        context.update({
            'title': 'Отчет сравнение периодов ' + str(month) + ' ' + str(year) + ' ' + str(month2) + ' ' + str(year2),

            # для периода 1
            'reports': reports,
            'years': years,
            'months': months,
            'segments': segments,
            'sites': sites,
            'year': year,
            'month': month,
            'segment': segment,
            'site': site,
            'total_budget': total_budget,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'total_unqualified_leads': total_unqualified_leads,
            'total_deals': total_deals,
            'total_qualified_deals': total_qualified_deals,
            'total_failed_deals': total_failed_deals,
            'total_ignored_failed_deals': total_ignored_failed_deals,
            'total_revenue': total_revenue,
            'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
            'avg_cpa_lead': avg_cpa_lead,
            'avg_cpa_deal': avg_cpa_deal,
            'avg_cpa_won_deal': avg_cpa_won_deal,
            'roi': roi,
            'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
            'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
            'direct_losses_ignored': direct_losses_ignored,
            'missed_profit': missed_profit,
            'revenue_per_qualified_deal': revenue_per_qualified_deal,
            'conversion_rate_unqualified': conversion_rate_unqualified,
            'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
            'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
            'conversion_rate_failed_deals': conversion_rate_failed_deals,
            'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
            # передаем средние
            'avg_budget': avg_budget,
            'avg_clicks': avg_clicks,
            'avg_leads': avg_leads,
            'avg_unqualified_leads': avg_unqualified_leads,
            'avg_deals': avg_deals,
            'avg_qualified_deals': avg_qualified_deals,
            'avg_failed_deals': avg_failed_deals,
            'avg_ignored_failed_deals': avg_ignored_failed_deals,
            'avg_revenue': avg_revenue,
            'avg_missed_profit_igore': avg_missed_profit_igore,
            # 'avg_direct_losses_ignored': avg_direct_losses_ignored,

            # для периода 2

            'reports2': reports2,
            'years2': years2,
            'months2': months2,
            'segments2': segments2,
            'sites2': sites2,
            'year2': year2,
            'month2': month2,
            'segment2': segment2,
            'site2': site2,
            'total_budget2': total_budget2,
            'total_clicks2': total_clicks2,
            'total_leads2': total_leads2,
            'total_unqualified_leads2': total_unqualified_leads2,
            'total_deals2': total_deals2,
            'total_qualified_deals2': total_qualified_deals2,
            'total_failed_deals2': total_failed_deals2,
            'total_ignored_failed_deals2': total_ignored_failed_deals2,
            'total_revenue2': total_revenue2,
            'average_conversion_rate2': f"{round((total_leads2 / total_clicks2) * 100, 2)}%" if total_clicks2 > 0 else "Н/Д",
            'avg_cpa_lead2': avg_cpa_lead2,
            'avg_cpa_deal2': avg_cpa_deal2,
            'avg_cpa_won_deal2': avg_cpa_won_deal2,
            'roi2': roi2,
            'conversion_rate_clicks_to_leads2': conversion_rate_clicks_to_leads2,
            'conversion_rate_leads_to_deals2': conversion_rate_leads_to_deals2,
            'direct_losses_ignored2': direct_losses_ignored2,
            'missed_profit2': missed_profit2,
            'revenue_per_qualified_deal2': revenue_per_qualified_deal2,
            'conversion_rate_unqualified2': conversion_rate_unqualified2,
            'conversion_rate_qualified_leds_to_deals2': conversion_rate_qualified_leds_to_deals2,
            'conversion_rate_qualified_deals2': conversion_rate_qualified_deals2,
            'conversion_rate_failed_deals2': conversion_rate_failed_deals2,
            'conversion_rate_ignored_failed_deals2': conversion_rate_ignored_failed_deals2,

            # Общие средние

            'avg_total_budget': (total_budget + total_budget2) / 2,
            'avg_total_clicks': (total_clicks + total_clicks2) / 2,
            'avg_total_leads': (total_leads + total_leads2) / 2,
            'avg_total_unqualified_leads': (total_unqualified_leads + total_unqualified_leads2) / 2,
            'avg_total_deals': (total_deals + total_deals2) / 2,
            'avg_total_qualified_deals': (total_qualified_deals + total_qualified_deals2) / 2,
            'avg_total_failed_deals': (total_failed_deals + total_failed_deals2) / 2,
            'avg_total_ignored_failed_deals': (total_ignored_failed_deals + total_ignored_failed_deals2) / 2,
            'avg_total_revenue': (total_revenue + total_revenue2) / 2,
            'avg_avg_cpa_lead': (avg_cpa_lead + avg_cpa_lead2) / 2,
            'avg_avg_cpa_deal': (avg_cpa_deal + avg_cpa_deal2) / 2,
            'avg_avg_cpa_won_deal': (avg_cpa_won_deal + avg_cpa_won_deal2) / 2,
            'avg_roi': (roi + roi2) / 2,
            'avg_conversion_rate_clicks_to_leads': (
                                                       conversion_rate_clicks_to_leads + conversion_rate_clicks_to_leads2) / 2,
            'avg_conversion_rate_leads_to_deals': (
                                                      conversion_rate_leads_to_deals + conversion_rate_leads_to_deals2) / 2,
            'avg_direct_losses_ignored': (direct_losses_ignored + direct_losses_ignored2) / 2,
            'avg_missed_profit': (missed_profit + missed_profit2) / 2,
            'avg_revenue_per_qualified_deal': (revenue_per_qualified_deal + revenue_per_qualified_deal2) / 2,
            'avg_conversion_rate_unqualified': (conversion_rate_unqualified + conversion_rate_unqualified2) / 2,
            'avg_conversion_rate_qualified_leds_to_deals': (
                                                               conversion_rate_qualified_leds_to_deals + conversion_rate_qualified_leds_to_deals2) / 2,
            'avg_conversion_rate_qualified_deals': (
                                                       conversion_rate_qualified_deals + conversion_rate_qualified_deals2) / 2,
            'avg_conversion_rate_failed_deals': (conversion_rate_failed_deals + conversion_rate_failed_deals2) / 2,
            'avg_conversion_rate_ignored_failed_deals': (
                                                            conversion_rate_ignored_failed_deals + conversion_rate_ignored_failed_deals2) / 2,

            # Общяя сумма

            'sum_total_budget': total_budget + total_budget2,
            'sum_total_clicks': total_clicks + total_clicks2,
            'sum_total_leads': total_leads + total_leads2,
            'sum_total_unqualified_leads': total_unqualified_leads + total_unqualified_leads2,
            'sum_total_deals': total_deals + total_deals2,
            'sum_total_qualified_deals': total_qualified_deals + total_qualified_deals2,
            'sum_total_failed_deals': total_failed_deals + total_failed_deals2,
            'sum_total_ignored_failed_deals': total_ignored_failed_deals3,
            'sum_total_revenue': total_revenue + total_revenue2,
            'sum_avg_cpa_lead': avg_cpa_lead3,
            'sum_avg_cpa_deal': avg_cpa_deal3,
            'sum_avg_cpa_won_deal': avg_cpa_won_deal3,
            'sum_roi': roi3,

            'sum_conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads3,
            'sum_conversion_rate_leads_to_deals': conversion_rate_leads_to_deals3,
            'sum_direct_losses_ignored': direct_losses_ignored + direct_losses_ignored2,
            'sum_missed_profit': missed_profit + missed_profit2,
            'sum_revenue_per_qualified_deal': revenue_per_qualified_deal3,
            'sum_conversion_rate_unqualified': conversion_rate_unqualified3,
            'sum_conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals3,
            'sum_conversion_rate_qualified_deals': conversion_rate_qualified_deals3,
            'sum_conversion_rate_failed_deals': conversion_rate_failed_deals3,
            'sum_conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals3,

            # Изменения

            'rost_total_budget': round((total_budget2 - total_budget) / total_budget * 100, 2),
            'rost_total_clicks': round((total_clicks2 - total_clicks) / total_clicks * 100, 2),
            'rost_total_leads': round((total_leads2 - total_leads) / total_leads * 100, 2),
            'rost_total_unqualified_leads': round(
                (total_unqualified_leads2 - total_unqualified_leads) / total_unqualified_leads * 100, 2),
            'rost_total_deals': round((total_deals2 - total_deals) / total_deals * 100, 2),
            'rost_total_qualified_deals': round(
                (total_qualified_deals2 - total_qualified_deals) / total_qualified_deals * 100, 2),
            'rost_total_failed_deals': round((total_failed_deals2 - total_failed_deals) / total_failed_deals * 100, 2),
            'rost_total_ignored_failed_deals': round(
                (total_ignored_failed_deals2 - total_ignored_failed_deals) / total_ignored_failed_deals * 100, 2),
            'rost_total_revenue': round((total_revenue2 - total_revenue) / total_revenue * 100, 2),
            'rost_avg_cpa_lead': round((avg_cpa_lead2 - avg_cpa_lead) / avg_cpa_lead * 100, 2),
            'rost_avg_cpa_deal': round((avg_cpa_deal2 - avg_cpa_deal) / avg_cpa_deal * 100, 2),
            'rost_avg_cpa_won_deal': round((avg_cpa_won_deal2 - avg_cpa_won_deal) / avg_cpa_won_deal * 100, 2),
            'rost_roi': round((roi2 - roi) / roi * 100, 2),
            'rost_conversion_rate_clicks_to_leads': round((
                                                              conversion_rate_clicks_to_leads2 - conversion_rate_clicks_to_leads) / conversion_rate_clicks_to_leads * 100,
                                                          2),
            'rost_conversion_rate_leads_to_deals': round((
                                                             conversion_rate_leads_to_deals2 - conversion_rate_leads_to_deals) / conversion_rate_leads_to_deals * 100,
                                                         2),
            'rost_direct_losses_ignored': round(
                (direct_losses_ignored2 - direct_losses_ignored) / direct_losses_ignored * 100, 2),
            'rost_missed_profit': round((missed_profit2 - missed_profit) / missed_profit * 100, 2),
            'rost_revenue_per_qualified_deal': round(
                (revenue_per_qualified_deal2 - revenue_per_qualified_deal) / revenue_per_qualified_deal * 100, 2),
            'rost_conversion_rate_unqualified': round(
                (conversion_rate_unqualified2 - conversion_rate_unqualified) / conversion_rate_unqualified * 100, 2),
            'rost_conversion_rate_qualified_leds_to_deals': round((
                                                                      conversion_rate_qualified_leds_to_deals2 - conversion_rate_qualified_leds_to_deals) / conversion_rate_qualified_leds_to_deals * 100,
                                                                  2),
            'rost_conversion_rate_qualified_deals': round((
                                                              conversion_rate_qualified_deals2 - conversion_rate_qualified_deals) / conversion_rate_qualified_deals * 100,
                                                          2),
            'rost_conversion_rate_failed_deals': round(
                (conversion_rate_failed_deals2 - conversion_rate_failed_deals) / conversion_rate_failed_deals * 100,
                2),
            'rost_conversion_rate_ignored_failed_deals': round((
                                                                   conversion_rate_ignored_failed_deals2 - conversion_rate_ignored_failed_deals) / conversion_rate_ignored_failed_deals * 100,
                                                               2),
        })

        return context


class ReportObsh(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year = self.request.GET.getlist('year')
        month = self.request.GET.getlist('month')
        segment = self.request.GET.getlist('segment')
        site = self.request.GET.getlist('site')

        reports = Report.objects.all()

        if year:
            reports = reports.filter(start_period__year__in=year)
        if month:
            reports = reports.filter(start_period__month__in=month)
        if segment:
            reports = reports.filter(segment__in=segment)
        if site:
            reports = reports.filter(site__in=site)

        years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                         flat=True).distinct().order_by(
            'month')
        segments = Report.objects.values_list('segment', flat=True).distinct()
        sites = Report.objects.values_list('site', flat=True).distinct()

        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

        avg_missed_profit_igore = 0
        count_missed_profit = 0
        for rep in reports:
            avg_missed_profit_igore += rep.missed_profit
            count_missed_profit += 1
        avg_missed_profit_igore = avg_missed_profit_igore / count_missed_profit

        avg_direct_losses_ignored = 0
        count_avg_direct_losses_ignored = 0
        for rep in reports:
            avg_direct_losses_ignored += rep.direct_losses_ignored
            count_avg_direct_losses_ignored += 1
        avg_direct_losses_ignored = avg_direct_losses_ignored / count_avg_direct_losses_ignored

        # Для периода 1
        # суммарные показатели

        total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                      'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                    'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals = reports.aggregate(Sum('failed_deals'))[
                                 'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                         'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else None  # Общий CPA Лида
        avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                                 2) if total_deals > 0 else None  # Общий CPA Выигранной Сделки
        roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                                2) if total_clicks > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                               2) if total_leads > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                      2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                           2) if total_qualified_deals > 0 else None  # Общий Средний чек
        conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                            2) if total_leads > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                        2) if total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                                2) if total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                             2) if total_deals > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                     2) if total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
            float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                              2) if total_deals > 0 else None  # Общий Упущенная прибыль

        # Средние показатели

        avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
        avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
        avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
        avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                    'unqualified_leads__avg'] or 0  # Среднее некач. лидов
        avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
        avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                                  'qualified_deals__avg'] or 0  # Среднее качественных сделок
        avg_failed_deals = reports.aggregate(Avg('failed_deals'))[
                               'failed_deals__avg'] or 0  # Среднее проваленных сделок
        avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                       'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
        avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

        context.update({
            'title': 'Общие показатели за ' + str(month) + ' ' + str(year),

            # для периода 1
            'reports': reports,
            'years': years,
            'months': months,
            'segments': segments,
            'sites': sites,
            'year': year,
            'month': month,
            'segment': segment,
            'site': site,
            'total_budget': total_budget,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'total_unqualified_leads': total_unqualified_leads,
            'total_deals': total_deals,
            'total_qualified_deals': total_qualified_deals,
            'total_failed_deals': total_failed_deals,
            'total_ignored_failed_deals': total_ignored_failed_deals,
            'total_revenue': total_revenue,
            'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
            'avg_cpa_lead': avg_cpa_lead,
            'avg_cpa_deal': avg_cpa_deal,
            'avg_cpa_won_deal': avg_cpa_won_deal,
            'roi': roi,
            'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
            'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
            'direct_losses_ignored': direct_losses_ignored,
            'missed_profit': missed_profit,
            'revenue_per_qualified_deal': revenue_per_qualified_deal,
            'conversion_rate_unqualified': conversion_rate_unqualified,
            'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
            'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
            'conversion_rate_failed_deals': conversion_rate_failed_deals,
            'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
            # передаем средние
            'avg_budget': avg_budget,
            'avg_clicks': avg_clicks,
            'avg_leads': avg_leads,
            'avg_unqualified_leads': avg_unqualified_leads,
            'avg_deals': avg_deals,
            'avg_qualified_deals': avg_qualified_deals,
            'avg_failed_deals': avg_failed_deals,
            'avg_ignored_failed_deals': avg_ignored_failed_deals,
            'avg_revenue': avg_revenue,
            'avg_missed_profit_igore': avg_missed_profit_igore,
        })

        return context


class ReportRus(TemplateView):

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        year = self.request.GET.getlist('year')
        month = self.request.GET.getlist('month')

        reports = Report.objects.all()

        if not month:
            if datetime.now().month == 1:
                month.append(12)
                year.append(datetime.now().year - 1)
            else:
                year.append(datetime.now().year)
                month.append(datetime.now().month - 1)

        reports = reports.filter(start_period__year__in=year)
        reports = reports.filter(start_period__month__in=month)

        years = Report.objects.annotate(year=ExtractYear('start_period')).values_list('year', flat=True).distinct()
        months = Report.objects.annotate(month=ExtractMonth('start_period')).values_list('month',
                                                                                         flat=True).distinct().order_by(
            'month')

        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])

        # Получаем текущий год и месяц
        current_year = int(year[0]) if year else datetime.now().year
        current_month = int(month[0]) if month else datetime.now().month

        year2 = []
        month2 = []

        # Вычисляем предыдущий месяц
        if current_month == 1:
            year2.append(current_year - 1)
            month2.append(12)
        else:
            year2.append(current_year)
            month2.append(current_month - 1)

        reports2 = Report.objects.all()
        reports2 = reports2.filter(start_period__year__in=year2)
        reports2 = reports2.filter(start_period__month__in=month2)

        avg_missed_profit_igore = 0
        count_missed_profit = 0
        for rep in reports:
            avg_missed_profit_igore += rep.missed_profit
            count_missed_profit += 1
        avg_missed_profit_igore = round(avg_missed_profit_igore / count_missed_profit, 2) if count_missed_profit > 0 else 0

        avg_direct_losses_ignored = 0
        count_avg_direct_losses_ignored = 0
        for rep in reports:
            avg_direct_losses_ignored += rep.direct_losses_ignored
            count_avg_direct_losses_ignored += 1
        avg_direct_losses_ignored = round(avg_direct_losses_ignored / count_avg_direct_losses_ignored, 2) if count_avg_direct_losses_ignored > 0 else 0

        # Для периода 1
        # суммарные показатели

        total_budget = reports.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks = reports.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads = reports.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads = reports.aggregate(Sum('unqualified_leads'))[
                                      'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals = reports.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals = reports.aggregate(Sum('qualified_deals'))[
                                    'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals = reports.aggregate(Sum('failed_deals'))[
                                 'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals = reports.aggregate(Sum('ignored_failed_deals'))[
                                         'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue = reports.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead = round(total_budget / total_leads, 2) if total_leads > 0 else 0  # Общий CPA Лида
        avg_cpa_deal = round(total_budget / total_deals, 2) if total_deals > 0 else 0  # Общий CPA Сделки
        avg_cpa_won_deal = round(total_budget / total_qualified_deals,
                                 2) if total_deals > 0 else 0  # Общий CPA Выигранной Сделки
        roi = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else 0  # Общий РОЙ
        conversion_rate_clicks_to_leads = round((total_leads / total_clicks * 100),
                                                2) if total_clicks > 0 else 0  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round((total_deals / total_leads * 100),
                                               2) if total_leads > 0 else 0  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(total_ignored_failed_deals * (avg_cpa_deal or 0),
                                      2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal = round(total_revenue / total_qualified_deals,
                                           2) if total_qualified_deals > 0 else 0  # Общий Средний чек
        conversion_rate_unqualified = round((total_unqualified_leads / total_leads * 100),
                                            2) if total_leads > 0 else 0  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round((total_qualified_deals / total_leads * 100),
                                                        2) if total_deals > 0 else 0  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round((total_qualified_deals / total_deals * 100),
                                                2) if total_deals > 0 else 0  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round((total_failed_deals / total_deals * 100),
                                             2) if total_deals > 0 else 0  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round((total_ignored_failed_deals / total_deals * 100),
                                                     2) if total_deals > 0 else 0  # Общий % провала Сделок по причине игнор дел

        missed_profit = round(((total_ignored_failed_deals * conversion_rate_qualified_deals / 100) * (
            float(revenue_per_qualified_deal) if revenue_per_qualified_deal is not None else 0)),
                              2) if total_deals > 0 else 0  # Общий Упущенная прибыль

        # Средние показатели

        avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
        avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
        avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
        avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                    'unqualified_leads__avg'] or 0  # Среднее некач. лидов
        avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
        avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                                  'qualified_deals__avg'] or 0  # Среднее качественных сделок
        avg_failed_deals = reports.aggregate(Avg('failed_deals'))[
                               'failed_deals__avg'] or 0  # Среднее проваленных сделок
        avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                       'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
        avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

        # Для периода 2
        # суммарные показатели

        total_budget2 = reports2.aggregate(Sum('budget'))['budget__sum'] or 0  # Сумма бюджета
        total_clicks2 = reports2.aggregate(Sum('clicks'))['clicks__sum'] or 0  # Сумма кликов
        total_leads2 = reports2.aggregate(Sum('leads'))['leads__sum'] or 0  # Сумма лидов
        total_unqualified_leads2 = reports2.aggregate(Sum('unqualified_leads'))[
                                       'unqualified_leads__sum'] or 0  # Сумма некач. лидов
        total_deals2 = reports2.aggregate(Sum('deals'))['deals__sum'] or 0  # Сумма сделок
        total_qualified_deals2 = reports2.aggregate(Sum('qualified_deals'))[
                                     'qualified_deals__sum'] or 0  # Сумма качественных сделок
        total_failed_deals2 = reports2.aggregate(Sum('failed_deals'))[
                                  'failed_deals__sum'] or 0  # Сумма проваленных сделок
        total_ignored_failed_deals2 = reports2.aggregate(Sum('ignored_failed_deals'))[
                                          'ignored_failed_deals__sum'] or 0  # Сумма некач. сделок игнор
        total_revenue2 = reports2.aggregate(Sum('revenue'))['revenue__sum'] or 0  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead2 = round(total_budget2 / total_leads2, 2) if total_leads2 > 0 else 0  # Общий CPA Лида
        avg_cpa_deal2 = round(total_budget2 / total_deals2, 2) if total_deals2 > 0 else 0  # Общий CPA Сделки
        avg_cpa_won_deal2 = round(total_budget2 / total_qualified_deals2,
                                  2) if total_deals2 > 0 else 0  # Общий CPA Выигранной Сделки
        roi2 = round((total_revenue2 - total_budget2) / total_budget2 * 100,
                     2) if total_budget2 > 0 else 0  # Общий РОЙ
        conversion_rate_clicks_to_leads2 = round((total_leads2 / total_clicks2 * 100),
                                                 2) if total_clicks2 > 0 else 0  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals2 = round((total_deals2 / total_leads2 * 100),
                                                2) if total_leads2 > 0 else 0  # Общий CR% Лидов в Сделки
        direct_losses_ignored2 = round(total_ignored_failed_deals2 * (avg_cpa_deal2 or 0),
                                       2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal2 = round(total_revenue2 / total_qualified_deals2,
                                            2) if total_qualified_deals2 > 0 else 0  # Общий Средний чек
        conversion_rate_unqualified2 = round((total_unqualified_leads2 / total_leads2 * 100),
                                             2) if total_leads2 > 0 else 0  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals2 = round((total_qualified_deals2 / total_leads2 * 100),
                                                         2) if total_deals2 > 0 else 0  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals2 = round((total_qualified_deals2 / total_deals2 * 100),
                                                 2) if total_deals2 > 0 else 0  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals2 = round((total_failed_deals2 / total_deals2 * 100),
                                              2) if total_deals2 > 0 else 0  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals2 = round((total_ignored_failed_deals2 / total_deals2 * 100),
                                                      2) if total_deals2 > 0 else 0  # Общий % провала Сделок по причине игнор дел

        missed_profit2 = round(((total_ignored_failed_deals2 * conversion_rate_qualified_deals2 / 100) * (
            float(revenue_per_qualified_deal2) if revenue_per_qualified_deal2 is not None else 0)),
                               2) if total_deals2 > 0 else 0  # Общий Упущенная прибыль

        # Для суммарного периода
        # суммарные показатели

        total_budget3 = total_budget + total_budget2
        total_clicks3 = total_clicks + total_clicks2  # Сумма кликов
        total_leads3 = total_leads + total_leads2
        total_unqualified_leads3 = total_unqualified_leads + total_unqualified_leads2  # Сумма некач. лидов
        total_deals3 = total_deals + total_deals2  # Сумма качественных сделок
        total_qualified_deals3 = total_qualified_deals + total_qualified_deals2  # Сумма качественных сделок
        total_failed_deals3 = total_failed_deals + total_failed_deals2  # Сумма проваленных сделок
        total_ignored_failed_deals3 = total_ignored_failed_deals + total_ignored_failed_deals2  # Сумма некач. сделок игнор
        total_revenue3 = total_revenue + total_revenue2  # Сумма выручки

        # Вычисления для отображения
        avg_cpa_lead3 = round(total_budget3 / total_leads3, 2) if total_leads3 > 0 else None  # Общий CPA Лида
        avg_cpa_deal3 = round(total_budget3 / total_deals3, 2) if total_deals3 > 0 else None  # Общий CPA Сделки
        avg_cpa_won_deal3 = round(total_budget3 / total_qualified_deals3,
                                  2) if total_deals3 > 0 else None  # Общий CPA Выигранной Сделки
        roi3 = round((total_revenue3 - total_budget3) / total_budget3 * 100,
                     2) if total_budget3 > 0 else None  # Общий РОЙ
        conversion_rate_clicks_to_leads3 = round((total_leads3 / total_clicks3 * 100),
                                                 2) if total_clicks3 > 0 else None  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals3 = round((total_deals3 / total_leads3 * 100),
                                                2) if total_leads3 > 0 else None  # Общий CR% Лидов в Сделки
        direct_losses_ignored3 = round(total_ignored_failed_deals3 * (avg_cpa_deal3 or 0),
                                       2)  # Общий Потери прямые по причине игнора дел

        # Добавим дополнительные значения для шаблона с округлением
        revenue_per_qualified_deal3 = round(total_revenue3 / total_qualified_deals3,
                                            2) if total_qualified_deals3 > 0 else None  # Общий Средний чек
        conversion_rate_unqualified3 = round((total_unqualified_leads3 / total_leads3 * 100),
                                             2) if total_leads3 > 0 else None  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals3 = round((total_qualified_deals3 / total_leads3 * 100),
                                                         2) if total_deals3 > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals3 = round((total_qualified_deals3 / total_deals3 * 100),
                                                 2) if total_deals3 > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals3 = round((total_failed_deals3 / total_deals3 * 100),
                                              2) if total_deals3 > 0 else None  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals3 = round((total_ignored_failed_deals3 / total_deals3 * 100),
                                                      2) if total_deals3 > 0 else None  # Общий % провала Сделок по причине игнор дел

        missed_profit3 = round(((total_ignored_failed_deals3 * conversion_rate_qualified_deals3 / 100) * (
            float(revenue_per_qualified_deal3) if revenue_per_qualified_deal3 is not None else 0)),
                               2) if total_deals3 > 0 else None  # Общий Упущенная прибыль

        # Средние показатели

        avg_budget = round(reports.aggregate(Avg('budget'))['budget__avg'] or 0, 2)  # Среднее бюджета
        avg_clicks = reports.aggregate(Avg('clicks'))['clicks__avg'] or 0  # Среднее кликов
        avg_leads = reports.aggregate(Avg('leads'))['leads__avg'] or 0  # Среднее лидов
        avg_unqualified_leads = reports.aggregate(Avg('unqualified_leads'))[
                                    'unqualified_leads__avg'] or 0  # Среднее некач. лидов
        avg_deals = reports.aggregate(Avg('deals'))['deals__avg'] or 0  # Среднее сделок
        avg_qualified_deals = reports.aggregate(Avg('qualified_deals'))[
                                  'qualified_deals__avg'] or 0  # Среднее качественных сделок
        avg_failed_deals = reports.aggregate(Avg('failed_deals'))[
                               'failed_deals__avg'] or 0  # Среднее проваленных сделок
        avg_ignored_failed_deals = reports.aggregate(Avg('ignored_failed_deals'))[
                                       'ignored_failed_deals__avg'] or 0  # Среднее некач. сделок игнор
        avg_revenue = reports.aggregate(Avg('revenue'))['revenue__avg'] or 0  # Среднее выручки

        reports_odin_dir = reports.filter(segment__in=[], site__in=['Одинцово'])
        reports_odin_seo = reports.filter(segment__in=[], site__in=[])
        reports_pod_dir = reports.filter(segment__in=[], site__in=[])
        reports_yacard = reports.filter(segment__in=[], site__in=[])

        context.update({
            'title': 'Отчет сравнение периодов ' + str(month) + ' ' + str(year) + ' ' + str(month2) + ' ' + str(year2),

            # для периода 1
            'reports': reports,
            'years': years,
            'months': months,
            'year': year,
            'month': month,
            'monthname': MONTHS[int(month[0])],
            'yearname': year[0],
            'total_budget': total_budget,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'total_unqualified_leads': total_unqualified_leads,
            'total_deals': total_deals,
            'total_qualified_deals': total_qualified_deals,
            'total_failed_deals': total_failed_deals,
            'total_ignored_failed_deals': total_ignored_failed_deals,
            'total_revenue': total_revenue,
            'average_conversion_rate': f"{round((total_leads / total_clicks) * 100, 2)}%" if total_clicks > 0 else "Н/Д",
            'avg_cpa_lead': avg_cpa_lead,
            'avg_cpa_deal': avg_cpa_deal,
            'avg_cpa_won_deal': avg_cpa_won_deal,
            'roi': roi,
            'conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads,
            'conversion_rate_leads_to_deals': conversion_rate_leads_to_deals,
            'direct_losses_ignored': direct_losses_ignored,
            'missed_profit': missed_profit,
            'revenue_per_qualified_deal': revenue_per_qualified_deal,
            'conversion_rate_unqualified': conversion_rate_unqualified,
            'conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals,
            'conversion_rate_qualified_deals': conversion_rate_qualified_deals,
            'conversion_rate_failed_deals': conversion_rate_failed_deals,
            'conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals,
            # передаем средние
            'avg_budget': avg_budget,
            'avg_clicks': avg_clicks,
            'avg_leads': avg_leads,
            'avg_unqualified_leads': avg_unqualified_leads,
            'avg_deals': avg_deals,
            'avg_qualified_deals': avg_qualified_deals,
            'avg_failed_deals': avg_failed_deals,
            'avg_ignored_failed_deals': avg_ignored_failed_deals,
            'avg_revenue': avg_revenue,
            'avg_missed_profit_igore': avg_missed_profit_igore,
            # 'avg_direct_losses_ignored': avg_direct_losses_ignored,

            # для периода 2

            'reports2': reports2,
            'year2': year2,
            'month2': month2,
            'yearname2': year2[0],
            'monthname2': MONTHS[month2[0]],
            'total_budget2': total_budget2,
            'total_clicks2': total_clicks2,
            'total_leads2': total_leads2,
            'total_unqualified_leads2': total_unqualified_leads2,
            'total_deals2': total_deals2,
            'total_qualified_deals2': total_qualified_deals2,
            'total_failed_deals2': total_failed_deals2,
            'total_ignored_failed_deals2': total_ignored_failed_deals2,
            'total_revenue2': total_revenue2,
            'average_conversion_rate2': f"{round((total_leads2 / total_clicks2) * 100, 2)}%" if total_clicks2 > 0 else "Н/Д",
            'avg_cpa_lead2': avg_cpa_lead2,
            'avg_cpa_deal2': avg_cpa_deal2,
            'avg_cpa_won_deal2': avg_cpa_won_deal2,
            'roi2': roi2,
            'conversion_rate_clicks_to_leads2': conversion_rate_clicks_to_leads2,
            'conversion_rate_leads_to_deals2': conversion_rate_leads_to_deals2,
            'direct_losses_ignored2': direct_losses_ignored2,
            'missed_profit2': missed_profit2,
            'revenue_per_qualified_deal2': revenue_per_qualified_deal2,
            'conversion_rate_unqualified2': conversion_rate_unqualified2,
            'conversion_rate_qualified_leds_to_deals2': conversion_rate_qualified_leds_to_deals2,
            'conversion_rate_qualified_deals2': conversion_rate_qualified_deals2,
            'conversion_rate_failed_deals2': conversion_rate_failed_deals2,
            'conversion_rate_ignored_failed_deals2': conversion_rate_ignored_failed_deals2,

            # Общие средние

            'avg_total_budget': (total_budget + total_budget2) / 2,
            'avg_total_clicks': (total_clicks + total_clicks2) / 2,
            'avg_total_leads': (total_leads + total_leads2) / 2,
            'avg_total_unqualified_leads': (total_unqualified_leads + total_unqualified_leads2) / 2,
            'avg_total_deals': (total_deals + total_deals2) / 2,
            'avg_total_qualified_deals': (total_qualified_deals + total_qualified_deals2) / 2,
            'avg_total_failed_deals': (total_failed_deals + total_failed_deals2) / 2,
            'avg_total_ignored_failed_deals': (total_ignored_failed_deals + total_ignored_failed_deals2) / 2,
            'avg_total_revenue': (total_revenue + total_revenue2) / 2,
            'avg_avg_cpa_lead': round((avg_cpa_lead + avg_cpa_lead2) / 2 or 0, 2),
            'avg_avg_cpa_deal': (avg_cpa_deal + avg_cpa_deal2) / 2,
            'avg_avg_cpa_won_deal': (avg_cpa_won_deal + avg_cpa_won_deal2) / 2,
            'avg_roi': (roi + roi2) / 2,
            'avg_conversion_rate_clicks_to_leads': (
                                                           conversion_rate_clicks_to_leads + conversion_rate_clicks_to_leads2) / 2,
            'avg_conversion_rate_leads_to_deals': round((conversion_rate_leads_to_deals + conversion_rate_leads_to_deals2) / 2,2),
            'avg_direct_losses_ignored': (direct_losses_ignored + direct_losses_ignored2) / 2,
            'avg_missed_profit': round((missed_profit + missed_profit2) / 2, 2),
            'avg_revenue_per_qualified_deal': (revenue_per_qualified_deal + revenue_per_qualified_deal2) / 2,
            'avg_conversion_rate_unqualified': (conversion_rate_unqualified + conversion_rate_unqualified2) / 2,
            'avg_conversion_rate_qualified_leds_to_deals': (
                                                                   conversion_rate_qualified_leds_to_deals + conversion_rate_qualified_leds_to_deals2) / 2,
            'avg_conversion_rate_qualified_deals': (
                                                           conversion_rate_qualified_deals + conversion_rate_qualified_deals2) / 2,
            'avg_conversion_rate_failed_deals': round((conversion_rate_failed_deals + conversion_rate_failed_deals2) / 2, 2),
            'avg_conversion_rate_ignored_failed_deals': (
                                                                conversion_rate_ignored_failed_deals + conversion_rate_ignored_failed_deals2) / 2,

            # Общяя сумма

            'sum_total_budget': total_budget + total_budget2,
            'sum_total_clicks': total_clicks + total_clicks2,
            'sum_total_leads': total_leads + total_leads2,
            'sum_total_unqualified_leads': total_unqualified_leads + total_unqualified_leads2,
            'sum_total_deals': total_deals + total_deals2,
            'sum_total_qualified_deals': total_qualified_deals + total_qualified_deals2,
            'sum_total_failed_deals': total_failed_deals + total_failed_deals2,
            'sum_total_ignored_failed_deals': total_ignored_failed_deals3,
            'sum_total_revenue': total_revenue + total_revenue2,
            'sum_avg_cpa_lead': avg_cpa_lead3,
            'sum_avg_cpa_deal': avg_cpa_deal3,
            'sum_avg_cpa_won_deal': avg_cpa_won_deal3,
            'sum_roi': roi3,

            'sum_conversion_rate_clicks_to_leads': conversion_rate_clicks_to_leads3,
            'sum_conversion_rate_leads_to_deals': conversion_rate_leads_to_deals3,
            'sum_direct_losses_ignored': direct_losses_ignored + direct_losses_ignored2,
            'sum_missed_profit': round(missed_profit + missed_profit2, 2),
            'sum_revenue_per_qualified_deal': revenue_per_qualified_deal3,
            'sum_conversion_rate_unqualified': conversion_rate_unqualified3,
            'sum_conversion_rate_qualified_leds_to_deals': conversion_rate_qualified_leds_to_deals3,
            'sum_conversion_rate_qualified_deals': conversion_rate_qualified_deals3,
            'sum_conversion_rate_failed_deals': conversion_rate_failed_deals3,
            'sum_conversion_rate_ignored_failed_deals': conversion_rate_ignored_failed_deals3,

            # Изменения

            'rost_total_budget': round((total_budget - total_budget2) / total_budget2 * 100, 2) if total_budget2 > 0 else 0,
            'rost_total_clicks': round((total_clicks - total_clicks2) / total_clicks2 * 100, 2) if total_clicks2 > 0 else 0,
            'rost_total_leads': round((total_leads - total_leads2) / total_leads2 * 100, 2) if total_leads2 > 0 else 0,
            'rost_total_unqualified_leads': round(
                (total_unqualified_leads - total_unqualified_leads2) / total_unqualified_leads2 * 100, 2) if total_unqualified_leads2 > 0 else 0,
            'rost_total_deals': round((total_deals - total_deals2) / total_deals2 * 100, 2) if total_deals2 > 0 else 0,
            'rost_total_qualified_deals': round(
                (total_qualified_deals - total_qualified_deals2) / total_qualified_deals2 * 100, 2) if total_qualified_deals2 > 0 else 0,
            'rost_total_failed_deals': round((total_failed_deals - total_failed_deals2) / total_failed_deals2 * 100, 2) if total_failed_deals2 > 0 else 0,
            'rost_total_ignored_failed_deals': round(
                (total_ignored_failed_deals - total_ignored_failed_deals2) / total_ignored_failed_deals2 * 100, 2) if total_ignored_failed_deals2 > 0 else 0,
            'rost_total_revenue': round((total_revenue - total_revenue2) / total_revenue2 * 100, 2) if total_revenue2 > 0 else 0,
            'rost_avg_cpa_lead': round((avg_cpa_lead - avg_cpa_lead2) / avg_cpa_lead2 * 100, 2) if avg_cpa_lead2 > 0 else 0,
            'rost_avg_cpa_deal': round((avg_cpa_deal - avg_cpa_deal2) / avg_cpa_deal2 * 100, 2) if avg_cpa_deal2 > 0 else 0,
            'rost_avg_cpa_won_deal': round((avg_cpa_won_deal - avg_cpa_won_deal2) / avg_cpa_won_deal2 * 100, 2) if avg_cpa_won_deal2 > 0 else 0,
            'rost_roi': round((roi - roi2) / roi2 * 100, 2) if roi2 > 0 else 0,
            'rost_conversion_rate_clicks_to_leads': round((conversion_rate_clicks_to_leads - conversion_rate_clicks_to_leads2) / conversion_rate_clicks_to_leads2 * 100, 2) if conversion_rate_clicks_to_leads2 > 0 else 0,
            'rost_conversion_rate_leads_to_deals': round((conversion_rate_leads_to_deals - conversion_rate_leads_to_deals2) / conversion_rate_leads_to_deals2 * 100, 2) if conversion_rate_leads_to_deals2 > 0 else 0,
            'rost_direct_losses_ignored': round(
                (direct_losses_ignored - direct_losses_ignored2) / direct_losses_ignored2 * 100, 2) if direct_losses_ignored2 > 0 else 0,
            'rost_missed_profit': round((missed_profit - missed_profit2) / missed_profit2 * 100, 2) if missed_profit2 > 0 else 0,
            'rost_revenue_per_qualified_deal': round(
                (revenue_per_qualified_deal - revenue_per_qualified_deal2) / revenue_per_qualified_deal2 * 100, 2) if revenue_per_qualified_deal2 > 0 else 0,
            'rost_conversion_rate_unqualified': round(
                (conversion_rate_unqualified - conversion_rate_unqualified2) / conversion_rate_unqualified2 * 100, 2) if conversion_rate_unqualified2 > 0 else 0,
            'rost_conversion_rate_qualified_leds_to_deals': round((
                                                                          conversion_rate_qualified_leds_to_deals - conversion_rate_qualified_leds_to_deals2) / conversion_rate_qualified_leds_to_deals2 * 100,
                                                                  2) if conversion_rate_qualified_leds_to_deals2 > 0 else 0,
            'rost_conversion_rate_qualified_deals': round((
                                                                  conversion_rate_qualified_deals - conversion_rate_qualified_deals2) / conversion_rate_qualified_deals2 * 100,
                                                          2) if conversion_rate_qualified_deals2 > 0 else 0,
            'rost_conversion_rate_failed_deals': round(
                (conversion_rate_failed_deals - conversion_rate_failed_deals2) / conversion_rate_failed_deals2 * 100,
                2) if conversion_rate_failed_deals2 > 0 else 0,
            'rost_conversion_rate_ignored_failed_deals': round((
                                                                       conversion_rate_ignored_failed_deals - conversion_rate_ignored_failed_deals2) / conversion_rate_ignored_failed_deals2 * 100,
                                                               2) if conversion_rate_ignored_failed_deals2 > 0 else 0,
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
            'title': 'Тест отчета',
            'total_budget': Report.total_sum_column('budget'),
            'total_revenue': Report.total_sum_column('revenue'),
            'total_deals': Report.total_sum_column('deals'),
            'budget': budget,
            'revenue': revenue,
        })


        return context

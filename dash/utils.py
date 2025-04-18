from decimal import Decimal, DivisionByZero, DivisionUndefined, InvalidOperation
from typing import List

from django.conf import settings

from .models import MONTHS, Report


def screenfilter(year, month, segment, site):
    mon = ''
    t = 0
    for m in month:
        if t == 0:
            mon += MONTHS[m]
        else:
            mon += ', ' + MONTHS[m]
        t += 1
    return (f'{",".join(year) or "Все Года"} | {mon or "Все Месяца"} | {",".join(segment) or "Все Сегменты"} | {",".join(site) or "Все Сайты"}')


def print_all_reports():
    from django_pandas.io import read_frame
    df = read_frame(Report.objects.all())
    for field in (
        'budget',
        'revenue',
        'cr_clicks_to_leads',
        'cr_leads_to_deals',
        'cr_non_quality',
        'conversion_leads_to_quality',
        'conversion_meetings_to_quality',
        'deals_failure_rate',
        'deals_failure_due_to_ignored',
        'cpa_lead',
        'cpa_deal',
        'cpa_won',
        'avg_check',
        'direct_losses_ignored',
        'missed_profit',
        'roi'
    ):
        df[field] = df[field].astype(float)
    df.to_excel('data.xlsx', index=False)


def get_report_data(year, month, segment=None, site=None):
    if settings.PRINT_ALL_REPORTS:
        print_all_reports()
    if segment is None:
        segment = list()
    if site is None:
        site = list()
    reports = Report.get_reports_by_params(year=year, month=month, segment=segment, site=site)
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

    # Средние показатели
    avg_data = Report.get_avg_data(year=year, month=month, segment=segment, site=site)

    result = {
        'reports': reports,
        'years': list(map(str, years)),
        'months': months,
        'segments': segments,
        'sites': sites,
        'year': list(map(str, year)),
        'month': month,
        'segment': segment,
        'site': site,
        **total_data,
        **presentation_data,
        **additional_data,
        # передаем средние
        **avg_data,
    }

    Report.cache_clear()

    return result


def get_report_data_by_two_periods(
    period1: List[List],
    period2: List[List]
):
    if settings.PRINT_ALL_REPORTS:
        print_all_reports()
    year, month, segment, site = period1
    year2, month2, segment2, site2 = period2

    for_filter = Report.get_list_of_variant()  # получаем варинты для фильтров на странице

    reports = Report.get_reports_by_params(year=year, month=month, segment=segment, site=site)  # получаем строки отчетов по фильтру
    reports2 = Report.get_reports_by_params(year=year2, month=month2, segment=segment2, site=site2)

    # Для периода 1
    # Суммарные показатели
    total_data = Report.get_total_data(year=year, month=month, segment=segment, site=site)

    # Вычисления для отображения
    presentation_data = Report.get_presentation_data(year=year, month=month, segment=segment, site=site)

    # Добавим дополнительные значения для шаблона с округлением
    additional_data = Report.get_additional_data(year=year, month=month, segment=segment, site=site)

    # Для периода 2
    # Суммарные показатели
    total_data_2 = Report.get_total_data(year=year2, month=month2, segment=segment2, site=site2)

    # Вычисления для отображения
    presentation_data_2 = Report.get_presentation_data(year=year2, month=month2, segment=segment2, site=site2)

    # Добавим дополнительные значения для шаблона с округлением
    additional_data_2 = Report.get_additional_data(year=year2, month=month2, segment=segment2, site=site2)

    # Для суммарного периода
    # суммарные показатели
    sum_total_budget = total_data['total_budget'] + total_data_2['total_budget']
    sum_total_clicks = total_data['total_clicks'] + total_data_2['total_clicks']  # Сумма кликов
    sum_total_leads = total_data['total_leads'] + total_data_2['total_leads']
    sum_total_unqualified_leads = total_data['total_unqualified_leads'] + total_data_2['total_unqualified_leads']  # Сумма некач. лидов
    sum_total_deals = total_data['total_deals'] + total_data_2['total_deals']  # Сумма качественных сделок
    sum_total_qualified_deals = total_data['total_qualified_deals'] + total_data_2['total_qualified_deals']  # Сумма качественных сделок
    sum_total_failed_deals = total_data['total_failed_deals'] + total_data_2['total_failed_deals']  # Сумма проваленных сделок
    sum_total_ignored_failed_deals = total_data['total_ignored_failed_deals'] + total_data_2['total_ignored_failed_deals']  # Сумма некач. сделок игнор
    sum_total_revenue = total_data['total_revenue'] + total_data_2['total_revenue']  # Сумма выручки
    sum_total_data = dict()
    for k in total_data.keys():
        sum_total_data[f'sum_{k}'] = total_data[k] + total_data_2[k]

    # Вычисления для отображения
    sum_avg_cpa_lead = round(sum_total_budget / sum_total_leads, 2) if sum_total_leads > 0 else None  # Общий CPA Лида
    sum_avg_cpa_deal = round(sum_total_budget / sum_total_deals, 2) if sum_total_deals > 0 else None  # Общий CPA Сделки
    sum_avg_cpa_won_deal = round(
        sum_total_budget / sum_total_qualified_deals, 2
    ) if sum_total_deals > 0 else None  # Общий CPA Выигранной Сделки
    sum_roi = round(
        (sum_total_revenue - sum_total_budget) / sum_total_budget * 100, 2
    ) if sum_total_budget > 0 else None  # Общий РОЙ
    sum_conversion_rate_clicks_to_leads = round(
        (sum_total_leads / sum_total_clicks * 100), 2
    ) if sum_total_clicks > 0 else None  # Общий CR% Кликов в Лиды
    sum_conversion_rate_leads_to_deals = round(
        (sum_total_deals / sum_total_leads * 100), 2
    ) if sum_total_leads > 0 else None  # Общий CR% Лидов в Сделки

    # Добавим дополнительные значения для шаблона с округлением
    sum_revenue_per_qualified_deal = round(
        sum_total_revenue / sum_total_qualified_deals, 2
    ) if sum_total_qualified_deals > 0 else None  # Общий Средний чек
    sum_conversion_rate_unqualified = round(
        (sum_total_unqualified_leads / sum_total_leads * 100), 2
    ) if sum_total_leads > 0 else None  # Общий CR% некач. Лидов
    sum_conversion_rate_qualified_leds_to_deals = round(
        (sum_total_qualified_deals / sum_total_leads * 100), 2
    ) if sum_total_deals > 0 else None  # % Общий % конверсии Обращений в Сделку качественную
    sum_conversion_rate_qualified_deals = round(
        (sum_total_qualified_deals / sum_total_deals * 100), 2
    ) if sum_total_deals > 0 else None  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
    sum_conversion_rate_failed_deals = round(
        (sum_total_failed_deals / sum_total_deals * 100), 2
    ) if sum_total_deals > 0 else None  # Общий % провала Сделок
    sum_conversion_rate_ignored_failed_deals = round(
        (sum_total_ignored_failed_deals / sum_total_deals * 100), 2
    ) if sum_total_deals > 0 else None  # Общий % провала Сделок по причине игнор дел

    # Средние показатели
    avg_data = Report.get_avg_data(year=year, month=month, segment=segment, site=site)

    all_periods_avg = Report.get_all_periods_avg_data()

    try:
        rost_total_qualified_deals = round((total_data_2['total_qualified_deals'] - total_data['total_qualified_deals']) / total_data['total_qualified_deals'] * 100, 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_total_qualified_deals = 0

    try:
        rost_total_qualified_deals_2 = round((total_data_2['total_qualified_deals'] - all_periods_avg['all_periods_avg_qualified_deals']) / all_periods_avg['all_periods_avg_qualified_deals'], 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_total_qualified_deals_2 = 0

    try:
        rost_total_ignored_failed_deals = round((total_data_2['total_ignored_failed_deals'] - total_data['total_ignored_failed_deals']) / total_data['total_ignored_failed_deals'] * 100, 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_total_ignored_failed_deals = total_data_2['total_ignored_failed_deals']

    try:
        rost_total_ignored_failed_deals_2 = round((total_data_2['total_ignored_failed_deals'] - all_periods_avg['all_periods_avg_ignored_failed_deals']) / all_periods_avg['all_periods_avg_ignored_failed_deals'], 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_total_ignored_failed_deals_2 = total_data_2['total_ignored_failed_deals']

    try:
        rost_direct_losses_ignored = round(
            (presentation_data_2['direct_losses_ignored'] - presentation_data['direct_losses_ignored']) / presentation_data['direct_losses_ignored'] * 100, 2
        )
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_direct_losses_ignored = presentation_data_2['direct_losses_ignored']

    try:
        rost_direct_losses_ignored_2 = round(
            (presentation_data_2['direct_losses_ignored'] - all_periods_avg['all_periods_avg_direct_losses_ignored_2']) / all_periods_avg['all_periods_avg_direct_losses_ignored_2'], 2
        )
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_direct_losses_ignored_2 = presentation_data_2['direct_losses_ignored']

    try:
        rost_missed_profit = round((additional_data_2['missed_profit'] - additional_data['missed_profit']) / additional_data['missed_profit'] * 100, 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_missed_profit = additional_data_2['missed_profit']

    try:
        rost_missed_profit_2 = round((additional_data_2['missed_profit'] - all_periods_avg['all_periods_avg_missed_profit']) / all_periods_avg['all_periods_avg_missed_profit'], 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_missed_profit_2 = additional_data_2['missed_profit']

    try:
        rost_conversion_rate_ignored_failed_deals = round((additional_data_2['conversion_rate_ignored_failed_deals'] - additional_data['conversion_rate_ignored_failed_deals']) / additional_data['conversion_rate_ignored_failed_deals'] * 100, 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_conversion_rate_ignored_failed_deals = additional_data_2['conversion_rate_ignored_failed_deals']

    try:
        rost_conversion_rate_ignored_failed_deals_2 = round((additional_data_2['conversion_rate_ignored_failed_deals'] - all_periods_avg['all_periods_avg_ignored_failed_deals']) / all_periods_avg['all_periods_avg_ignored_failed_deals'], 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_conversion_rate_ignored_failed_deals_2 = additional_data_2['conversion_rate_ignored_failed_deals']

    try:
        rost_conversion_rate_failed_deals = round((additional_data_2['conversion_rate_failed_deals'] - additional_data['conversion_rate_failed_deals']) / additional_data['conversion_rate_failed_deals'] * 100, 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_conversion_rate_failed_deals = 0

    try:
        rost_conversion_rate_failed_deals_2 = round((additional_data_2['conversion_rate_failed_deals'] - all_periods_avg['all_periods_avg_failed_deals']) / all_periods_avg['all_periods_avg_failed_deals'], 2)
    except (ZeroDivisionError, ValueError, DivisionUndefined, DivisionByZero, InvalidOperation):
        rost_conversion_rate_failed_deals_2 = 0

    result = {
        # для фильтра
        'years': list(map(str, for_filter['years'])),
        'months': for_filter['months'],
        'segments': for_filter['segments'],
        'sites': for_filter['sites'],

        # для периода 1
        'reports': reports,
        'year': year,
        'month': month,
        'segment': segment,
        'site': site,
        "namefilter": screenfilter(map(str, year), month, segment, site),

        **total_data,
        **presentation_data,
        **additional_data,
        # передаем средние
        **avg_data,

        # для периода 2
        'reports2': reports2,
        'year2': year2,
        'month2': month2,
        'segment2': segment2,
        'site2': site2,
        "namefilter2": screenfilter(map(str, year2), month2, segment2, site2),
        **{f'{k}2': v for k, v in total_data_2.items()},
        **{f'{k}2': v for k, v in presentation_data_2.items()},
        **{f'{k}2': v for k, v in additional_data_2.items()},

        # Общие средние
        'avg_total_budget': round(sum_total_budget / 2, 2),
        'avg_total_clicks': round(sum_total_clicks / 2, 2),
        'avg_total_leads': round(sum_total_leads / 2, 2),
        'avg_total_unqualified_leads': round(sum_total_unqualified_leads / 2, 2),
        'avg_total_deals': round(sum_total_deals / 2, 2),
        'avg_total_qualified_deals': round(sum_total_qualified_deals / 2, 2),
        'avg_total_failed_deals': round(sum_total_failed_deals / 2, 2),
        'avg_total_ignored_failed_deals': round(sum_total_ignored_failed_deals / 2, 2),
        'avg_total_revenue': round(sum_total_revenue / 2, 2),
        'avg_avg_cpa_lead': round((presentation_data['avg_cpa_lead'] + presentation_data_2['avg_cpa_lead']) / 2, 2),
        'avg_avg_cpa_deal': round((presentation_data['avg_cpa_deal'] + presentation_data_2['avg_cpa_deal']) / 2, 2),
        'avg_avg_cpa_won_deal': round((presentation_data['avg_cpa_won_deal'] + presentation_data_2['avg_cpa_won_deal']) / 2, 2),
        'avg_roi': round((presentation_data['roi'] + presentation_data_2['roi']) / 2, 2),
        'avg_conversion_rate_clicks_to_leads': round((presentation_data['conversion_rate_clicks_to_leads'] + presentation_data_2['conversion_rate_clicks_to_leads']) / 2, 2),
        'avg_conversion_rate_leads_to_deals': round((presentation_data['conversion_rate_leads_to_deals'] + presentation_data_2['conversion_rate_leads_to_deals']) / 2, 2),
        'avg_direct_losses_ignored': round((presentation_data['direct_losses_ignored'] + presentation_data_2['direct_losses_ignored']) / 2, 2),
        'avg_missed_profit': round((additional_data['missed_profit'] + additional_data_2['missed_profit']) / 2, 2),
        'avg_revenue_per_qualified_deal': round((additional_data['revenue_per_qualified_deal'] + additional_data_2['revenue_per_qualified_deal']) / 2, 2),
        'avg_conversion_rate_unqualified': round((additional_data['conversion_rate_unqualified'] + additional_data_2['conversion_rate_unqualified']) / 2, 2),
        'avg_conversion_rate_qualified_leds_to_deals': round((additional_data['conversion_rate_qualified_leds_to_deals'] + additional_data_2['conversion_rate_qualified_leds_to_deals']) / 2, 2),
        'avg_conversion_rate_qualified_deals': round((additional_data['conversion_rate_qualified_deals'] + additional_data_2['conversion_rate_qualified_deals']) / 2, 2),
        'avg_conversion_rate_failed_deals': round((additional_data['conversion_rate_failed_deals'] + additional_data_2['conversion_rate_failed_deals']) / 2, 2),
        'avg_conversion_rate_ignored_failed_deals': round((additional_data['conversion_rate_ignored_failed_deals'] + additional_data_2['conversion_rate_ignored_failed_deals']) / 2, 2),

        # Общяя сумма
        'sum_total_budget': sum_total_budget,
        'sum_total_clicks': sum_total_clicks,
        'sum_total_leads': sum_total_leads,
        'sum_total_unqualified_leads': sum_total_unqualified_leads,
        'sum_total_deals': sum_total_deals,
        'sum_total_qualified_deals': sum_total_qualified_deals,
        'sum_total_failed_deals': sum_total_failed_deals,
        'sum_total_ignored_failed_deals': sum_total_ignored_failed_deals,
        'sum_total_revenue': sum_total_revenue,
        'sum_avg_cpa_lead': sum_avg_cpa_lead,
        'sum_avg_cpa_deal': sum_avg_cpa_deal,
        'sum_avg_cpa_won_deal': sum_avg_cpa_won_deal,
        'sum_roi': sum_roi,
        'sum_conversion_rate_clicks_to_leads': sum_conversion_rate_clicks_to_leads,
        'sum_conversion_rate_leads_to_deals': sum_conversion_rate_leads_to_deals,
        'sum_direct_losses_ignored': presentation_data['direct_losses_ignored'] + presentation_data_2['direct_losses_ignored'],
        'sum_missed_profit': additional_data['missed_profit'] + additional_data_2['missed_profit'],
        'sum_revenue_per_qualified_deal': sum_revenue_per_qualified_deal,
        'sum_conversion_rate_unqualified': sum_conversion_rate_unqualified,
        'sum_conversion_rate_qualified_leds_to_deals': sum_conversion_rate_qualified_leds_to_deals,
        'sum_conversion_rate_qualified_deals': sum_conversion_rate_qualified_deals,
        'sum_conversion_rate_failed_deals': sum_conversion_rate_failed_deals,
        'sum_conversion_rate_ignored_failed_deals': sum_conversion_rate_ignored_failed_deals,

        # Изменения
        'rost_total_budget': round((total_data_2['total_budget'] - total_data['total_budget']) / total_data['total_budget'] * 100, 2) if total_data['total_budget'] else Decimal(0.0),
        'rost_total_clicks': round((total_data_2['total_clicks'] - total_data['total_clicks']) / total_data['total_clicks'] * 100, 2) if total_data['total_clicks'] else Decimal(0.0),
        'rost_total_leads': round((total_data_2['total_leads'] - total_data['total_leads']) / total_data['total_leads'] * 100, 2) if total_data['total_leads'] else Decimal(0.0),
        'rost_total_unqualified_leads': round((total_data_2['total_unqualified_leads'] - total_data['total_unqualified_leads']) / total_data['total_unqualified_leads'] * 100, 2) if total_data['total_unqualified_leads'] else Decimal(0.0),
        'rost_total_deals': round((total_data_2['total_deals'] - total_data['total_deals']) / total_data['total_deals'] * 100, 2) if total_data['total_deals'] else Decimal(0.0),
        'rost_total_qualified_deals': rost_total_qualified_deals,
        'rost_total_failed_deals': round((total_data_2['total_failed_deals'] - total_data['total_failed_deals']) / total_data['total_failed_deals'] * 100, 2) if total_data['total_failed_deals'] else Decimal(0.0),
        'rost_total_ignored_failed_deals': rost_total_ignored_failed_deals,
        'rost_total_revenue': round((total_data_2['total_revenue'] - total_data['total_revenue']) / total_data['total_revenue'] * 100, 2) if total_data['total_revenue'] else Decimal(0.0),
        'rost_avg_cpa_lead': round((presentation_data_2['avg_cpa_lead'] - presentation_data['avg_cpa_lead']) / presentation_data['avg_cpa_lead'] * 100, 2) if presentation_data['avg_cpa_lead'] else Decimal(0.0),
        'rost_avg_cpa_deal': round((presentation_data_2['avg_cpa_deal'] - presentation_data['avg_cpa_deal']) / presentation_data['avg_cpa_deal'] * 100, 2) if presentation_data['avg_cpa_deal'] else Decimal(0.0),
        'rost_avg_cpa_won_deal': round((presentation_data_2['avg_cpa_won_deal'] - presentation_data['avg_cpa_won_deal']) / presentation_data['avg_cpa_won_deal'] * 100, 2) if presentation_data['avg_cpa_won_deal'] else Decimal(0.0),
        'rost_roi': round((presentation_data_2['roi'] - presentation_data['roi']) / presentation_data['roi'] * 100, 2) if presentation_data['roi'] else Decimal(0.0),
        'rost_conversion_rate_clicks_to_leads': round(
            (presentation_data_2['conversion_rate_clicks_to_leads'] - presentation_data['conversion_rate_clicks_to_leads']) / presentation_data['conversion_rate_clicks_to_leads'] * 100,
            2
        ) if presentation_data['conversion_rate_clicks_to_leads'] else Decimal(0.0),
        'rost_conversion_rate_leads_to_deals': round(
            (presentation_data_2['conversion_rate_leads_to_deals'] - presentation_data['conversion_rate_leads_to_deals']) / presentation_data['conversion_rate_leads_to_deals'] * 100,
            2
        ) if presentation_data['conversion_rate_leads_to_deals'] else Decimal(0.0),
        'rost_direct_losses_ignored': rost_direct_losses_ignored,
        'rost_missed_profit': rost_missed_profit,
        'rost_revenue_per_qualified_deal': round(
            (additional_data_2['revenue_per_qualified_deal'] - additional_data['revenue_per_qualified_deal']) / additional_data['revenue_per_qualified_deal'] * 100, 2) if additional_data['revenue_per_qualified_deal'] else Decimal(0.0),
        'rost_conversion_rate_unqualified': round(
            (additional_data_2['conversion_rate_unqualified'] - additional_data['conversion_rate_unqualified']) / additional_data['conversion_rate_unqualified'] * 100, 2) if additional_data['conversion_rate_unqualified'] else Decimal(0.0),
        'rost_conversion_rate_qualified_leds_to_deals': round(
            (additional_data_2['conversion_rate_qualified_leds_to_deals'] - additional_data['conversion_rate_qualified_leds_to_deals']) / additional_data['conversion_rate_qualified_leds_to_deals'] * 100,
            2
        ) if additional_data['conversion_rate_qualified_leds_to_deals'] else Decimal(0.0),
        'rost_conversion_rate_qualified_deals': round(
            (additional_data_2['conversion_rate_qualified_deals'] - additional_data['conversion_rate_qualified_deals']) / additional_data['conversion_rate_qualified_deals'] * 100,
            2
        ) if additional_data['conversion_rate_qualified_deals'] else Decimal(0.0),
        'rost_conversion_rate_failed_deals': rost_conversion_rate_failed_deals,
        'rost_conversion_rate_ignored_failed_deals': rost_conversion_rate_ignored_failed_deals,

        **all_periods_avg,

        # Изменения от общих средних
        'rost_total_budget_2': round((total_data_2['total_budget'] - all_periods_avg['all_periods_avg_budget']) / all_periods_avg['all_periods_avg_budget'], 2) if all_periods_avg['all_periods_avg_budget'] else Decimal(0.0),
        'rost_total_clicks_2': round((total_data_2['total_clicks'] - all_periods_avg['all_periods_avg_clicks']) / all_periods_avg['all_periods_avg_clicks'], 2) if all_periods_avg['all_periods_avg_clicks'] else Decimal(0.0),
        'rost_total_leads_2': round((total_data_2['total_leads'] - all_periods_avg['all_periods_avg_leads']) / all_periods_avg['all_periods_avg_leads'], 2) if all_periods_avg['all_periods_avg_leads'] else Decimal(0.0),
        'rost_total_unqualified_leads_2': round((total_data_2['total_unqualified_leads'] - all_periods_avg['all_periods_avg_unqualified_leads']) / all_periods_avg['all_periods_avg_unqualified_leads'], 2) if all_periods_avg['all_periods_avg_unqualified_leads'] else Decimal(0.0),
        'rost_total_deals_2': round((total_data_2['total_deals'] - all_periods_avg['all_periods_avg_deals']) / all_periods_avg['all_periods_avg_deals'], 2) if all_periods_avg['all_periods_avg_deals'] else Decimal(0.0),
        'rost_total_qualified_deals_2': rost_total_qualified_deals_2,
        'rost_total_failed_deals_2': round((total_data_2['total_failed_deals'] - all_periods_avg['all_periods_avg_failed_deals']) / all_periods_avg['all_periods_avg_failed_deals'], 2) if all_periods_avg['all_periods_avg_failed_deals'] else Decimal(0.0),
        'rost_total_ignored_failed_deals_2': rost_total_ignored_failed_deals_2,
        'rost_total_revenue_2': round((total_data_2['total_revenue'] - all_periods_avg['all_periods_avg_revenue']) / all_periods_avg['all_periods_avg_revenue'], 2) if all_periods_avg['all_periods_avg_revenue'] else Decimal(0.0),
        'rost_avg_cpa_lead_2': round((presentation_data_2['avg_cpa_lead'] - all_periods_avg['all_periods_avg_cpa_lead']) / all_periods_avg['all_periods_avg_cpa_lead'], 2) if all_periods_avg['all_periods_avg_cpa_lead'] else Decimal(0.0),
        'rost_avg_cpa_deal_2': round((presentation_data_2['avg_cpa_deal'] - all_periods_avg['all_periods_avg_cpa_deal']) / all_periods_avg['all_periods_avg_cpa_deal'], 2) if all_periods_avg['all_periods_avg_cpa_deal'] else Decimal(0.0),
        'rost_avg_cpa_won_deal_2': round((presentation_data_2['avg_cpa_won_deal'] - all_periods_avg['all_periods_avg_cpa_won_deal']) / all_periods_avg['all_periods_avg_cpa_won_deal'], 2) if all_periods_avg['all_periods_avg_cpa_won_deal'] else Decimal(0.0),
        'rost_roi_2': round((presentation_data_2['roi'] - all_periods_avg['roi']) / all_periods_avg['roi'], 2) if all_periods_avg['roi'] else Decimal(0.0),
        'rost_conversion_rate_clicks_to_leads_2': round(
            (presentation_data_2['conversion_rate_clicks_to_leads'] - all_periods_avg['all_periods_avg_clicks_to_leads']) / all_periods_avg['all_periods_avg_clicks_to_leads'],
            2
        ) if all_periods_avg['all_periods_avg_clicks_to_leads'] else Decimal(0.0),
        'rost_conversion_rate_leads_to_deals_2': round(
            (presentation_data_2['conversion_rate_leads_to_deals'] - all_periods_avg['all_periods_avg_leads_to_deals']) / all_periods_avg['all_periods_avg_leads_to_deals'],
            2
        ) if all_periods_avg['all_periods_avg_leads_to_deals'] else Decimal(0.0),
        'rost_direct_losses_ignored_2': rost_direct_losses_ignored_2,
        'rost_missed_profit_2': rost_missed_profit_2,
        'rost_revenue_per_qualified_deal_2': round(
            (additional_data_2['revenue_per_qualified_deal'] - all_periods_avg['revenue_per_qualified_deal']) / all_periods_avg['revenue_per_qualified_deal'], 2) if all_periods_avg['revenue_per_qualified_deal'] else Decimal(0.0),
        'rost_conversion_rate_unqualified_2': round(
            (additional_data_2['conversion_rate_unqualified'] - all_periods_avg['all_periods_avg_unqualified']) / all_periods_avg['all_periods_avg_unqualified'], 2) if all_periods_avg['all_periods_avg_unqualified'] else Decimal(0.0),
        'rost_conversion_rate_qualified_leds_to_deals_2': round(
            (additional_data_2['conversion_rate_qualified_leds_to_deals'] - all_periods_avg['all_periods_avg_qualified_leds_to_deals']) / all_periods_avg['all_periods_avg_qualified_leds_to_deals'],
            2
        ) if all_periods_avg['all_periods_avg_qualified_leds_to_deals'] else Decimal(0.0),
        'rost_conversion_rate_qualified_deals_2': round(
            (additional_data_2['conversion_rate_qualified_deals'] - all_periods_avg['all_periods_avg_qualified_deals']) / all_periods_avg['all_periods_avg_qualified_deals'],
            2
        ) if all_periods_avg['all_periods_avg_qualified_deals'] else Decimal(0.0),
        'rost_conversion_rate_failed_deals_2': rost_conversion_rate_failed_deals_2,
        'rost_conversion_rate_ignored_failed_deals_2': rost_conversion_rate_ignored_failed_deals_2,
    }

    Report.cache_clear()

    return result

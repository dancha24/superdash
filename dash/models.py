from collections import defaultdict
from decimal import Decimal
from functools import cache

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Sum
from django.db.models.functions import ExtractMonth, ExtractYear

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


class Report(models.Model):
    start_period = models.DateField("Начало периода")
    end_period = models.DateField("Конец периода")
    site = models.CharField("Сайт", max_length=100)
    segment = models.CharField("Сегмент", max_length=100)
    budget = models.DecimalField("Бюджет", max_digits=12, decimal_places=2)
    clicks = models.IntegerField("Клики")
    leads = models.IntegerField("Кол-во Лидов")
    unqualified_leads = models.IntegerField("Кол-во некач. Лидов")
    deals = models.IntegerField("Кол-во Сделок")
    qualified_deals = models.IntegerField("Кол-во Сделок качественных")
    failed_deals = models.IntegerField("Кол-во проваленных Сделок")
    ignored_failed_deals = models.IntegerField("Кол-во проваленных Сделок по причине игнор дел")
    revenue = models.DecimalField("Выручка", max_digits=14, decimal_places=2)

    def clean(self):
        if any(
            field < 0
            for field in [
                self.clicks,
                self.leads,
                self.deals,
                self.qualified_deals,
                self.failed_deals,
                self.ignored_failed_deals
            ]
        ):
            raise ValidationError("Показатели кликов, лидов и сделок не могут быть отрицательными.")

    def __str__(self):
        return f"{self.site} - {self.segment} ({self.start_period} - {self.end_period})"

    # CR% Кликов в Лиды
    @property
    def cr_clicks_to_leads(self) -> float:
        return round((self.leads / self.clicks * 100), 2) if self.clicks > 0 else None

    # CR% Лидов в Сделки
    @property
    def cr_leads_to_deals(self) -> float:
        return round((self.deals / self.leads * 100), 2) if self.leads > 0 else None

    # CR% некач. Лидов
    @property
    def cr_non_quality(self) -> float:
        return round((self.unqualified_leads / self.leads * 100), 2) if self.leads > 0 else None

    # % конверсии Обращений в Сделку качественную
    @property
    def conversion_leads_to_quality(self) -> float:
        return round((self.qualified_deals / self.leads * 100), 2) if self.leads > 0 else None

    # % конверсии в Сделку качественную (после стадии "Встреча")
    @property
    def conversion_meetings_to_quality(self) -> float:
        return round((self.qualified_deals / self.deals * 100), 2) if self.deals > 0 else None

    # % провала Сделок
    @property
    def deals_failure_rate(self) -> float:
        return round((self.failed_deals / self.deals * 100), 2) if self.deals > 0 else None

    # % провала Сделок по причине игнор дел
    @property
    def deals_failure_due_to_ignored(self) -> float:
        return round((self.ignored_failed_deals / self.deals * 100), 2) if self.deals > 0 else None

    # CPA Лид
    @property
    def cpa_lead(self) -> float:
        return round(float(self.budget) / self.leads, 2) if self.leads > 0 else None

    # CPA Сделка
    @property
    def cpa_deal(self) -> float:
        return round(float(self.budget) / self.deals, 2) if self.deals > 0 else None

    # CPA выигранной Сделки
    @property
    def cpa_won(self) -> float:
        return round(float(self.budget) / self.qualified_deals, 2) if self.qualified_deals > 0 else None

    # Средний чек
    @property
    def avg_check(self) -> float:
        return round(float(self.revenue) / self.qualified_deals, 2) if self.qualified_deals > 0 else None

    # Потери прямые по причине игнора дел
    @property
    def direct_losses_ignored(self) -> float:
        return round(self.ignored_failed_deals * self.cpa_deal, 2) if self.ignored_failed_deals > 0 else 0

    # Упущенная прибыль
    @property
    def missed_profit(self) -> float:
        return round((self.ignored_failed_deals * self.conversion_meetings_to_quality / 100) * (self.avg_check or 0), 2) if self.ignored_failed_deals > 0 else 0

    # РОЙ
    @property
    def roi(self) -> float:
        return round((float(self.revenue) - float(self.budget)) / float(self.budget) * 100, 2) if self.budget > 0 else None

    @classmethod
    def total_sum_column(cls, name, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        return queryset.aggregate(total=Sum(name))['total'] or 0

    @classmethod
    def get_name_list(cls, name, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        return list(queryset.values_list(name, flat=True))

    # варианты полей для фильтров
    @classmethod
    def get_list_of_variant(cls):
        return {
            'years': cls.get_years(),
            'months': cls.get_months(),
            'segments': cls.get_segments(),
            'sites': cls.get_sites(),
        }

    class Meta:
        verbose_name = "Отчет"
        verbose_name_plural = "Отчеты"

    @classmethod
    def get_segments(cls):
        return cls.objects.values_list('segment', flat=True).distinct()

    @classmethod
    def get_sites(cls):
        return cls.objects.values_list('site', flat=True).distinct()

    @classmethod
    def get_years(cls):
        return cls.objects.annotate(
            year=ExtractYear('start_period')
        ).values_list(
            'year', flat=True
        ).distinct().order_by('year')

    @classmethod
    def get_months(cls):
        months = cls.objects.annotate(
            month=ExtractMonth('start_period')
        ).values_list(
            'month', flat=True
        ).distinct().order_by('month')
        months = sorted([(m, MONTHS[m]) for m in months if m in MONTHS.keys()])
        return months

    @classmethod
    @cache
    def get_reports_by_params(cls, **params):
        print('get reports', params)
        _reports = cls.objects.all()
        for field_name in (
            'year',
            'month',
            'segment',
            'site'
        ):
            if field_name in params and params[field_name]:
                if field_name == 'year':
                    _field = 'start_period__year__in'
                elif field_name == 'month':
                    _field = 'start_period__month__in'
                else:
                    _field = f'{field_name}__in'
                _reports = _reports.filter(**{_field: params[field_name]})
        return _reports

    @classmethod
    def get_value_field(cls, data_type, field_name, **params):
        _reports = cls.get_reports_by_params(**params)
        if data_type == 'avg':
            value = _reports.aggregate(Avg(field_name))[f'{field_name}__avg'] or 0
        elif data_type == 'total':
            value = _reports.aggregate(Sum(field_name))[f'{field_name}__sum'] or 0
        return round(Decimal(value), 2)

    @classmethod
    def get_budget(cls, data_type, **params):
        return cls.get_value_field(data_type, 'budget', **params)

    @classmethod
    def get_clicks(cls, data_type, **params):
        return cls.get_value_field(data_type, 'clicks', **params)

    @classmethod
    def get_leads(cls, data_type, **params):
        return cls.get_value_field(data_type, 'leads', **params)

    @classmethod
    def get_unqualified_leads(cls, data_type, **params):
        return cls.get_value_field(data_type, 'unqualified_leads', **params)

    @classmethod
    def get_deals(cls, data_type, **params):
        return cls.get_value_field(data_type, 'deals', **params)

    @classmethod
    def get_qualified_deals(cls, data_type, **params):
        return cls.get_value_field(data_type, 'qualified_deals', **params)

    @classmethod
    def get_failed_deals(cls, data_type, **params):
        return cls.get_value_field(data_type, 'failed_deals', **params)

    @classmethod
    def get_ignored_failed_deals(cls, data_type, **params):
        return cls.get_value_field(data_type, 'ignored_failed_deals', **params)

    @classmethod
    def get_revenue(cls, data_type, **params):
        return cls.get_value_field(data_type, 'revenue', **params)

    @classmethod
    def get_data_by_type(cls, data_type: str, **params):
        data_type_list = ('avg', 'total')
        if data_type not in data_type_list:
            raise ValueError(f'Invalid data type. Must be in list ({", ".join(data_type_list)})')
        data = defaultdict(lambda: Decimal(0.0))
        for field in (
            'budget',
            'clicks',
            'leads',
            'unqualified_leads',
            'deals',
            'qualified_deals',
            'failed_deals',
            'ignored_failed_deals',
            'revenue'
        ):
            method_name = f'get_{field}'
            method = getattr(Report, method_name)
            data[f'{data_type}_{field}'] = method(data_type, **params)
        return data

    @classmethod
    def get_avg_data(cls, **params):
        avg_data = cls.get_data_by_type('avg', **params)
        return avg_data

    @classmethod
    def get_total_data(cls, **params):
        """Суммарные показатели"""
        total_data = cls.get_data_by_type('total', **params)
        return total_data

    @classmethod
    def get_presentation_data(cls, **params):
        """Вычисления для отображения"""
        total_data = cls.get_total_data(**params)

        avg_cpa_lead = round(
            total_data['total_budget'] / total_data['total_leads'], 2
        ) if total_data['total_leads'] > 0 else 0.0  # Общий CPA Лида
        avg_cpa_deal = round(
            total_data['total_budget'] / total_data['total_deals'], 2
        ) if total_data['total_deals'] > 0 else 0.0  # Общий CPA Сделки
        avg_cpa_won_deal = round(
            total_data['total_budget'] / total_data['total_qualified_deals'], 2
        ) if total_data['total_deals'] > 0 else 0.0  # Общий CPA Выигранной Сделки
        roi = round(
            (total_data['total_revenue'] - total_data['total_budget']) / total_data['total_budget'] * 100, 2
        ) if total_data['total_budget'] > 0 else 0.0  # Общий РОЙ
        conversion_rate_clicks_to_leads = round(
            (total_data['total_leads'] / total_data['total_clicks'] * 100), 2
        ) if total_data['total_clicks'] > 0 else 0.0  # Общий CR% Кликов в Лиды
        conversion_rate_leads_to_deals = round(
            (total_data['total_deals'] / total_data['total_leads'] * 100), 2
        ) if total_data['total_leads'] > 0 else 0.0  # Общий CR% Лидов в Сделки
        direct_losses_ignored = round(
            total_data['total_ignored_failed_deals'] * (avg_cpa_deal or 0), 2
        )  # Общий Потери прямые по причине игнора дел

        return {
            'avg_cpa_lead': Decimal(avg_cpa_lead),
            'avg_cpa_deal': Decimal(avg_cpa_deal),
            'avg_cpa_won_deal': Decimal(avg_cpa_won_deal),
            'roi': Decimal(roi),
            'conversion_rate_clicks_to_leads': Decimal(conversion_rate_clicks_to_leads),
            'conversion_rate_leads_to_deals': Decimal(conversion_rate_leads_to_deals),
            'direct_losses_ignored': Decimal(direct_losses_ignored),
        }

    @classmethod
    def get_additional_data(cls, **params):
        """Дополнительные значения для шаблона с округлением"""
        total_data = cls.get_total_data(**params)

        revenue_per_qualified_deal = round(
            total_data['total_revenue'] / total_data['total_qualified_deals'], 2
        ) if total_data['total_qualified_deals'] > 0 else 0.0  # Общий Средний чек
        conversion_rate_unqualified = round(
            (total_data['total_unqualified_leads'] / total_data['total_leads'] * 100), 2
        ) if total_data['total_leads'] > 0 else 0.0  # Общий CR% некач. Лидов
        conversion_rate_qualified_leds_to_deals = round(
            (total_data['total_qualified_deals'] / total_data['total_leads'] * 100), 2
        ) if total_data['total_deals'] > 0 else 0.0  # % Общий % конверсии Обращений в Сделку качественную
        conversion_rate_qualified_deals = round(
            (total_data['total_qualified_deals'] / total_data['total_deals'] * 100), 2
        ) if total_data['total_deals'] > 0 else 0.0  # % Общий конверсии в Сделку качественную (после стадии "Встреча")
        conversion_rate_failed_deals = round(
            (total_data['total_failed_deals'] / total_data['total_deals'] * 100), 2
        ) if total_data['total_deals'] > 0 else 0.0  # Общий % провала Сделок
        conversion_rate_ignored_failed_deals = round(
            (total_data['total_ignored_failed_deals'] / total_data['total_deals'] * 100), 2
        ) if total_data['total_deals'] > 0 else 0.0  # Общий % провала Сделок по причине игнор дел
        missed_profit = round(
            (
                (
                    total_data['total_ignored_failed_deals'] * Decimal(conversion_rate_qualified_deals) / 100
                ) * (
                    Decimal(revenue_per_qualified_deal) if revenue_per_qualified_deal else Decimal(0.0)
                )
            ),
            2
        ) if total_data['total_deals'] > 0 else 0.0  # Общий Упущенная прибыль

        return {
            'revenue_per_qualified_deal': Decimal(revenue_per_qualified_deal),
            'conversion_rate_unqualified': Decimal(conversion_rate_unqualified),
            'conversion_rate_qualified_leds_to_deals': Decimal(conversion_rate_qualified_leds_to_deals),
            'conversion_rate_qualified_deals': Decimal(conversion_rate_qualified_deals),
            'conversion_rate_failed_deals': Decimal(conversion_rate_failed_deals),
            'conversion_rate_ignored_failed_deals': Decimal(conversion_rate_ignored_failed_deals),
            'missed_profit': Decimal(missed_profit)
        }

    @classmethod
    def cache_clear(cls):
        cls.get_reports_by_params.cache_clear()

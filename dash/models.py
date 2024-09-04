from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum


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
        if any(field < 0 for field in [self.clicks, self.leads, self.deals,
                                        self.qualified_deals, self.failed_deals,
                                        self.ignored_failed_deals]):
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

    class Meta:
        verbose_name = "Отчет"
        verbose_name_plural = "Отчеты"

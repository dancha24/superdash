import csv
from datetime import datetime

from django.core.management.base import BaseCommand

from dash.models import Report


class Command(BaseCommand):
    help = 'Load data into the Report model'

    def handle(self, *args, **kwargs):
        file_path = 'C:/Users/danch/PycharmProjects/superdash/dash/data.csv'  # Укажите путь к вашему CSV-файлу

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Report.objects.create(
                    start_period=datetime.strptime(row['Начало периода'], '%d.%m.%Y'),
                    end_period=datetime.strptime(row['Конец периода'], '%d.%m.%Y'),
                    site=row['Сайт'],
                    segment=row['Сегмент'],
                    budget=float(row['Бюджет']),
                    clicks=int(row['Клики']),
                    leads=int(row['Кол-во Лидов']),
                    unqualified_leads=int(row['Кол-во некач. Лидов']),
                    deals=int(row['Кол-во Сделок']),
                    qualified_deals=int(row['Кол-во Сделок качественных']),
                    failed_deals=int(row['Кол-во проваленных Сделок']),
                    ignored_failed_deals=int(row['Кол-во проваленных Сделок по причине игнор дел']),
                    revenue=float(row['Выручка'])
                )
        self.stdout.write(self.style.SUCCESS('Data loaded successfully'))

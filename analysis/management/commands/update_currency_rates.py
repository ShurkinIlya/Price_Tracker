import requests
from django.core.management.base import BaseCommand

from analysis.models import CurrencyRate


class Command(BaseCommand):
    help = "Обновляет курсы валют из ЦБ (latest.js) и сохраняет в БД."

    def handle(self, *args, **options):
        try:
            resp = requests.get("https://www.cbr-xml-daily.ru/latest.js", timeout=8)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})
            updated = 0
            for code, val in rates.items():
                inv = 1 / float(val)
                CurrencyRate.objects.update_or_create(code=code, defaults={"rate": inv})
                updated += 1
            self.stdout.write(self.style.SUCCESS(f"Обновлено курсов: {updated}"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Не удалось обновить курсы: {exc}"))

import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.management import call_command


class Command(BaseCommand):
    help = "Запускает цикл автообновления цен (вместо cron). Останавливайте вручную (Ctrl+C)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=7200,
            help="Интервал в секундах между обновлениями (по умолчанию 2 часа).",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        self.stdout.write(self.style.SUCCESS(f"Старт автообновления каждые {interval} секунд"))
        while True:
            start = timezone.now()
            self.stdout.write(self.style.NOTICE(f"[{start}] refresh_prices..."))
            try:
                call_command("refresh_prices")
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Ошибка refresh_prices: {exc}"))
            time.sleep(interval)

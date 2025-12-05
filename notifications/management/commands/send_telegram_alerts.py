import os
import requests
from django.core.management.base import BaseCommand

from notifications.models import TelegramSubscription
from products.models import Offer, OfferHistory


class Command(BaseCommand):
    help = "Send telegram alerts (demo): notify users about latest offers for their queries"

    def handle(self, *args, **options):
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            self.stdout.write(self.style.WARNING("TELEGRAM_BOT_TOKEN not set, skip alerts"))
            return

        for sub in TelegramSubscription.objects.filter(is_active=True):
            last_offer = (
                Offer.objects.filter(query__created_by=sub.user)
                .order_by("-parsed_at")
                .first()
            )
            if not last_offer:
                continue
            text = f"Последнее обновление: {last_offer.title}\nЦена: {last_offer.price} {last_offer.currency}"
            self._send(token, sub.chat_id, text)
        self.stdout.write(self.style.SUCCESS("Telegram alerts processed"))

    def _send(self, token: str, chat_id: str, text: str):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
        except Exception as exc:
            print(f"Send telegram failed: {exc}")

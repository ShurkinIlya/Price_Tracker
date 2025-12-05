from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from products.models import ProductQuery, Offer, OfferHistory
from products.services import fetch_offers_from_marketplaces
from products.currency import to_rub


class Command(BaseCommand):
    help = "Refresh prices for all product queries (used for cron/auto-refresh)"

    def handle(self, *args, **options):
        queries = ProductQuery.objects.all()
        for q in queries:
            raw_offers = fetch_offers_from_marketplaces(
                product_name=q.name, marketplaces=["amazon", "wildberries", "ozon"]
            )
            if not raw_offers:
                continue
            q.offers.all().delete()
            offers_to_create = []
            for raw in raw_offers:
                if raw.get("price") in (None, "", 0):
                    continue
                marketplace = raw.get("marketplace", "amazon")
                raw_price = float(raw.get("price", 0))
                if marketplace == "amazon":
                    price = raw_price
                    currency = "USD"
                else:
                    price = to_rub(raw_price, raw.get("currency", "RUB"))
                    currency = "RUB"
                offers_to_create.append(
                    Offer(
                        query=q,
                        marketplace=marketplace,
                        title=raw.get("title", q.name),
                        price=Decimal(str(price)) if price else 0,
                        currency=currency,
                        rating=raw.get("rating"),
                        url=raw.get("url", ""),
                        image_url=raw.get("image_url", ""),
                    )
                )
            Offer.objects.bulk_create(offers_to_create)
            for offer in offers_to_create:
                OfferHistory.objects.create(
                    query=q,
                    marketplace=offer.marketplace,
                    title=offer.title,
                    price=offer.price,
                    currency=offer.currency,
                )
        self.stdout.write(self.style.SUCCESS("Prices refreshed"))

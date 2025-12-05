from django.db import models
from django.contrib.auth import get_user_model


class ProductQuery(models.Model):
    MARKETPLACE_CHOICES = [
        ("amazon", "Amazon"),
        ("wildberries", "Wildberries"),
        ("ozon", "Ozon"),
    ]

    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    marketplaces = models.CharField(
        max_length=120,
        help_text="Comma-separated marketplaces to query",
        default="amazon,wildberries,ozon",
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.category or 'без категории'})"


class Offer(models.Model):
    MARKETPLACE_CHOICES = [
        ("amazon", "Amazon"),
        ("wildberries", "Wildberries"),
        ("ozon", "Ozon"),
    ]

    query = models.ForeignKey(
        ProductQuery, related_name="offers", on_delete=models.CASCADE
    )
    marketplace = models.CharField(max_length=32, choices=MARKETPLACE_CHOICES)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    parsed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]

    def __str__(self) -> str:
        return f"{self.title} - {self.marketplace}"


class PriceAlert(models.Model):
    query = models.ForeignKey(
        ProductQuery, related_name="alerts", on_delete=models.CASCADE
    )
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Alert for {self.query.name} @ {self.target_price}"


class OfferHistory(models.Model):
    query = models.ForeignKey(
        ProductQuery, related_name="history", on_delete=models.CASCADE
    )
    marketplace = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-collected_at"]

    def __str__(self) -> str:
        return f"{self.title} {self.price} {self.currency} ({self.marketplace})"

from django.contrib import admin

from .models import ProductQuery, Offer, PriceAlert


@admin.register(ProductQuery)
class ProductQueryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "created_by", "created_at")
    search_fields = ("name", "category")
    list_filter = ("created_at",)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "marketplace", "price", "currency", "rating", "parsed_at")
    list_filter = ("marketplace", "parsed_at")
    search_fields = ("title",)


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ("query", "target_price", "is_active", "created_at")
    list_filter = ("is_active", "created_at")

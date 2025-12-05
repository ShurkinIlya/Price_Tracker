from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from analysis.seasonal_analyzer import SeasonalAnalyzer
from analysis.predictor import PricePredictor
from analysis.advanced_predictor import advanced_predict
from .models import Offer, ProductQuery, OfferHistory, PriceAlert
from .services import fetch_offers_from_marketplaces, generate_demo_offers
from .currency import to_rub


def home_view(request):
    recent_queries = ProductQuery.objects.order_by("-created_at")[:5]
    recent_offers = Offer.objects.select_related("query").order_by("price")[:6]
    return render(
        request,
        "pages/home.html",
        {"recent_queries": recent_queries, "recent_offers": recent_offers},
    )


def product_list(request):
    if not request.user.is_authenticated:
        messages.error(request, "Авторизуйтесь, чтобы видеть историю предложений.")
        return redirect("login")
    offers = (
        Offer.objects.select_related("query")
        .filter(query__created_by=request.user)
        .order_by("-parsed_at")[:50]
    )
    # вычисляем тренд по истории
    for offer in offers:
        prev = (
            OfferHistory.objects.filter(
                query=offer.query,
                marketplace=offer.marketplace,
                collected_at__lt=offer.parsed_at,
            )
            .order_by("-collected_at")
            .first()
        )
        if prev:
            diff = offer.price - prev.price
            offer.trend = "up" if diff > 0 else "down" if diff < 0 else "flat"
            offer.diff_value = diff
            offer.diff_abs = abs(diff)
        else:
            offer.trend = "flat"
            offer.diff_value = 0
            offer.diff_abs = 0
    return render(request, "products/list.html", {"offers": offers})


@login_required
def product_search(request):
    if request.method == "POST":
        product_name = request.POST.get("product_name", "").strip()
        if not product_name:
            messages.error(request, "Введите название товара.")
            return redirect("product_search")
        url = f"{reverse('search_results')}?q={product_name}"
        return redirect(url)

    return render(request, "pages/product_search.html")


@login_required
def search_results(request):
    search_query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip() or "electronics"
    if not search_query:
        messages.error(request, "Введите запрос для поиска.")
        return redirect("product_search")

    existing_query = ProductQuery.objects.filter(
        name__iexact=search_query, category=category
    ).order_by("-created_at").first()

    # если есть свежие офферы (<= 1 час) и не демо — отдаём их, иначе парсим заново
    reuse = False
    force_refresh = request.GET.get("refresh") == "1"
    if existing_query:
        offers_qs = existing_query.offers.order_by("-parsed_at")
        if offers_qs.exists():
            latest = offers_qs.first().parsed_at
            if not force_refresh and latest >= timezone.now() - timedelta(hours=1):
                reuse = True
                query_obj = existing_query
                offers = list(offers_qs)
    if not reuse:
        query_obj = existing_query or ProductQuery.objects.create(
            name=search_query,
            category=category,
            created_by=request.user if request.user.is_authenticated else None,
        )
        # очистить старые офферы перед новым парсингом
        query_obj.offers.all().delete()

    raw_offers = fetch_offers_from_marketplaces(
        product_name=search_query,
        marketplaces=["amazon", "wildberries", "ozon"],
    )
    used_demo = False
    offers = []
    if reuse:
        used_demo = False
    else:
        if not raw_offers:
            raw_offers = []
            used_demo = False
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
            offer = Offer.objects.create(
                query=query_obj,
                marketplace=marketplace,
                title=raw.get("title", search_query),
                price=Decimal(str(price)) if price else 0,
                currency=currency,
                rating=raw.get("rating"),
                url=raw.get("url", ""),
                image_url=raw.get("image_url", ""),
            )
            OfferHistory.objects.create(
                query=query_obj,
                marketplace=offer.marketplace,
                title=offer.title,
                price=offer.price,
                currency=offer.currency,
            )
            offers.append(offer)

    forecast = None
    forecast_confidence_pct = None
    if offers:
        # сначала пытаемся продвинутый прогноз
        forecast = advanced_predict(query_obj.id, category, offers[0].marketplace)
        # если не удалось — fallback
        if not forecast:
            forecast = PricePredictor().predict(query_obj.id, category)
        if forecast and forecast.get("confidence") is not None:
            forecast_confidence_pct = round(forecast["confidence"] * 100, 1)

    return render(
        request,
        "pages/search_results.html",
        {
            "search_query": search_query,
            "category": category,
            "results": offers,
            "results_count": len(offers),
            "used_demo": used_demo if 'used_demo' in locals() else False,
            "forecast": forecast,
            "forecast_confidence_pct": forecast_confidence_pct,
            "forecast_trend": forecast.get("trend") if forecast else None,
        },
    )


@login_required
def create_price_alert(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    try:
        query_id = int(request.POST.get("query_id"))
        target_price = request.POST.get("target_price")
        target_price = Decimal(str(target_price))
    except Exception:
        return HttpResponseBadRequest("Invalid data")
    query = ProductQuery.objects.filter(id=query_id, created_by=request.user).first()
    if not query:
        return HttpResponseBadRequest("Query not found")
    alert = PriceAlert.objects.create(query=query, target_price=target_price, is_active=True)
    return JsonResponse({"status": "ok", "alert_id": alert.id})

from django.contrib import admin
from django.urls import include, path

from accounts import views as accounts_views
from notifications import urls as notification_urls
from products import views as product_views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path("", product_views.home_view, name="home"),
    path("admin/", admin.site.urls),
    path("login/", accounts_views.login_view, name="login"),
    path("register/", accounts_views.register_view, name="register"),
    path("logout/", accounts_views.logout_view, name="logout"),
    path("profile/", accounts_views.profile_view, name="profile"),
    path("clear-history/", accounts_views.clear_history, name="clear_history"),
    path("products/", include("products.urls")),
    path("search/", product_views.product_search, name="product_search"),
    path("results/", product_views.search_results, name="search_results"),
    path("notifications/", include(notification_urls)),
]

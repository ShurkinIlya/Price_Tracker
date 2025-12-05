from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('search/', views.product_search, name='product_search'),
    path('results/', views.search_results, name='search_results'),
    path('create-alert/', views.create_price_alert, name='create_price_alert'),
]

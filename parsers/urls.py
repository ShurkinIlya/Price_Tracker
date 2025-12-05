# parsers/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='parsers_index'),
    path('amazon/', views.amazon_parser, name='amazon_parser'),
    path('wildberries/', views.wildberries_parser, name='wildberries_parser'),
    path('ozon/', views.ozon_parser, name='ozon_parser'),
]
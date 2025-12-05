# analysis/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='analysis_index'),
    path('predict/', views.price_prediction, name='price_prediction'),
]
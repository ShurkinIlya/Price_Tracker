from django.urls import path
from . import views

app_name = 'accounts'  # Исправьте на 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('clear-history/', views.clear_history, name='clear_history'),
]

from django.urls import path
from .views import dashboard

app_name = 'equipo'

urlpatterns = [
    path('', dashboard, name='dashboard'),
]
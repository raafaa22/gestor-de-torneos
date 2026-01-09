from django.urls import path
from .views import jugador_dashboard, organizador_dashboard

app_name = 'torneo'

urlpatterns = [
    path('jugador/', jugador_dashboard, name='jugador'),
    path('organizador/', organizador_dashboard, name='organizador'),
]
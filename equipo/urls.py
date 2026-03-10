from django.urls import path
from .views import dashboard, dar_baja_torneo, listado_jugadores, listado_torneos_inscribir

app_name = 'equipo'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('dar-baja/<int:torneo_id>/', dar_baja_torneo, name='dar_baja_torneo'),
    path('listado-torneos/<int:equipo_id>/', listado_torneos_inscribir, name='listado_torneos_inscribir'),
    path('listado-jugadores/<int:equipo_id>/', listado_jugadores, name='listado_jugadores'),
]
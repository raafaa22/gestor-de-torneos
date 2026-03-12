from django.urls import path
from .views import dashboard, dar_baja_torneo, listado_jugadores, listado_torneos_inscribir, editar_jugador, crear_jugador, borrar_jugador,\
inscribir_equipo_torneo

app_name = 'equipo'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('dar-baja/<int:torneo_id>/', dar_baja_torneo, name='dar_baja_torneo'),
    path('listado-torneos/<int:equipo_id>/', listado_torneos_inscribir, name='listado_torneos_inscribir'),
    path('listado-torneos/<int:equipo_id>/inscribir/<int:torneo_id>/', inscribir_equipo_torneo, name='inscribirse'),
    path('jugadores/<int:equipo_id>/', listado_jugadores, name='listado_jugadores'),
    path('jugadores/<int:equipo_id>/editar/<str:jugador_id>/', editar_jugador, name='editar_jugador'),
    path('jugadores/<int:equipo_id>/crear/', crear_jugador, name='crear_jugador'),
    path('jugadores/<int:equipo_id>/borrar/<str:jugador_id>/', borrar_jugador, name='borrar_jugador'),
]
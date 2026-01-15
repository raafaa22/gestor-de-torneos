from django.urls import path
from .views import borrar_torneo, jugador_dashboard, organizador_dashboard, crear_torneo, principal_torneo

app_name = 'torneo'

urlpatterns = [
    path('jugador/', jugador_dashboard, name='jugador'),
    path('organizador/', organizador_dashboard, name='organizador'),
    path('organizador/borrar/<int:torneo_id>/', borrar_torneo, name='borrar_torneo'),
    path('crear/', crear_torneo, name='crear_torneo'),
    path('organizador/torneo/<int:torneo_id>/', principal_torneo, name='principal_torneo'),
]
from django.urls import path
from .views import borrar_torneo, jugador_dashboard, organizador_dashboard, crear_torneo, principal_torneo, clasificacion_torneo, enfrentamientos_torneo,\
informacion_torneo, estadisticas_torneo, equipos_torneo

app_name = 'torneo'

urlpatterns = [
    path('jugador/', jugador_dashboard, name='jugador'),
    path('organizador/', organizador_dashboard, name='organizador'),
    path('organizador/borrar/<int:torneo_id>/', borrar_torneo, name='borrar_torneo'),
    path('crear/', crear_torneo, name='crear_torneo'),
    path('<int:torneo_id>/', principal_torneo, name='principal_torneo'),
    path('<int:torneo_id>/clasificacion/', clasificacion_torneo, name='clasificacion_torneo'),
    path('<int:torneo_id>/enfrentamientos/', enfrentamientos_torneo, name='enfrentamientos_torneo'),
    path('<int:torneo_id>/informacion/', informacion_torneo, name='informacion_torneo'),
    path('<int:torneo_id>/estadisticas/', estadisticas_torneo, name='estadisticas_torneo'),
    path('<int:torneo_id>/equipos/', equipos_torneo, name='equipos_torneo'),
]
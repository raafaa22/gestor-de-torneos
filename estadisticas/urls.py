from django.urls import path
from .views import estadisticas_torneo, jugador_estadisticas_detalle

app_name = 'estadisticas'


urlpatterns = [
    path('torneo/<int:torneo_id>/estadisticas/', estadisticas_torneo, name='estadisticas_torneo'),
    path('torneo/<int:torneo_id>/jugador/<str:jugador_dni>/', jugador_estadisticas_detalle, name='jugador_estadisticas_detalle'),
]


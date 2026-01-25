from django.urls import path
from .views import estadisticas_torneo

app_name = 'estadisticas'


urlpatterns = [
    path('torneo/<int:torneo_id>/estadisticas/', estadisticas_torneo, name='estadisticas_torneo'),
]


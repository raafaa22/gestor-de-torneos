from django.urls import path
from .views import enfrentamientos_torneo, editar_enfrentamiento, detalle_enfrentamiento

app_name = 'enfrentamientos'

urlpatterns = [
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>', enfrentamientos_torneo, name='enfrentamientos_torneo'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/detalle/<int:enfrentamiento_id>', detalle_enfrentamiento, name='detalle_enfrentamiento'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/editar/<int:enfrentamiento_id>', editar_enfrentamiento, name='editar_enfrentamiento'),
]
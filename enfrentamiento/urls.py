from django.urls import path
from .views import enfrentamientos_torneo, editar_enfrentamiento, detalle_enfrentamiento, guardar_enfrentamiento, borrar_estadistica, guardar_estadistica,\
    generar_enfrentamientos_aleatorios, generar_enfrentamientos_personalizados

app_name = 'enfrentamientos'

urlpatterns = [
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>', enfrentamientos_torneo, name='enfrentamientos_torneo'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/detalle/<int:enfrentamiento_id>', detalle_enfrentamiento, name='detalle_enfrentamiento'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/editar/<int:enfrentamiento_id>', editar_enfrentamiento, name='editar_enfrentamiento'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/editar/<int:enfrentamiento_id>/estadistica/<int:equipo_id>', guardar_estadistica, name='guardar_estadistica'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/editar/<int:enfrentamiento_id>/guardar', guardar_enfrentamiento, name='guardar_enfrentamiento'),
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/editar/<int:enfrentamiento_id>/borrar/<int:estadistica_id>', borrar_estadistica, name='borrar_estadistica'),
    path('<int:torneo_id>/enfrentamientos/generar_pers/', generar_enfrentamientos_personalizados, name='generar_personalizados'),
    path('<int:torneo_id>/enfrentamientos/generar_aleatorios/', generar_enfrentamientos_aleatorios, name='generar_aleatorios'),
]
from django.urls import path
from .views import enfrentamientos_torneo

app_name = 'enfrentamientos'

urlpatterns = [
    path('<int:torneo_id>/enfrentamientos/<int:n_ronda>/', enfrentamientos_torneo, name='enfrentamientos_torneo'),
]
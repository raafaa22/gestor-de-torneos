from django.urls import path
from .views import registro, login, admin_dashboard, home, logout, perfil

app_name = 'usuario'


urlpatterns = [
    path('registro/', registro, name='registro'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('', home, name='home'),
    path('perfil/', perfil, name='perfil'),
    path('administrador/', admin_dashboard, name='administrador'),
]
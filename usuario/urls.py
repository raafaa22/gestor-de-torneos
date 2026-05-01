from django.urls import path

from enfrentamiento import views
from .views import registro, login, admin_dashboard, home, logout, perfil, usuarios, borrar_usuario,\
    editar_usuario, crear_usuario, health, cambiar_password_obligatorio, validar_password

app_name = 'usuario'


urlpatterns = [
    path('registro/', registro, name='registro'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('', home, name='home'),
    path('perfil/', perfil, name='perfil'),
    path('cambiar-password-obligatorio/', cambiar_password_obligatorio, name='cambiar_password_obligatorio'),
    path('validar-password/', validar_password, name='validar_password'),
    path('administrador/', admin_dashboard, name='administrador'),
    path('administrador/usuarios/', usuarios, name='listado_usuarios'),
    path('administrador/usuarios/borrar/<int:usuario_id>/', borrar_usuario, name='borrar_usuario'),
    path('administrador/usuarios/editar/<int:usuario_id>/', editar_usuario, name='editar_usuario'),
    path('administrador/usuarios/crear/', crear_usuario, name='crear_usuario'),
    path("health/", health, name="health")
]
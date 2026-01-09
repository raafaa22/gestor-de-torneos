from django.urls import path
from .views import registro, login, admin_dashboard, post_login

app_name = 'usuario'


urlpatterns = [
    path('registro/', registro, name='registro'),
    path('login/', login, name='login'),
    path('administrador/', admin_dashboard, name='administrador'),
]
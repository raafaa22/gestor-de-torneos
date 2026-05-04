from django.utils.translation import gettext_lazy as _
from gestor.choices import TipoUsuario
from .models import Organizador, Jugador, Administrador
from equipo.models import Equipo


def nombre_usuario(request):
    if request.user.is_authenticated:
        admin = Administrador.objects.filter(user=request.user).first()
        if admin:
            return {'nombre_usuario': admin.nombre, 'tipo_usuario_nav': _('Administrador')}

        organizador = Organizador.objects.filter(user=request.user).first()
        if organizador:
            return {'nombre_usuario': organizador.nombre, 'tipo_usuario_nav': _('Organizador')}

        equipo = Equipo.objects.filter(user=request.user).first()
        if equipo:
            return {'nombre_usuario': equipo.nombre, 'tipo_usuario_nav': _('Equipo')}

        jugador = Jugador.objects.filter(user=request.user).first()
        if jugador:
            return {'nombre_usuario': jugador.nombre, 'tipo_usuario_nav': _('Jugador')}

    return {}
    

from .models import Organizador, Jugador, Administrador
from equipo.models import Equipo


def nombre_usuario(request):
    if request.user.is_authenticated:
        admin = Administrador.objects.filter(user=request.user).first()
        if admin:
            return {'nombre_usuario': admin.nombre}
        
        organizador = Organizador.objects.filter(user=request.user).first()
        if organizador:
            return {'nombre_usuario': organizador.nombre}
        
        equipo = Equipo.objects.filter(user=request.user).first()
        if equipo:
            return {'nombre_usuario': equipo.nombre}
        
        jugador = Jugador.objects.filter(user=request.user).first()
        if jugador:
            return {'nombre_usuario': jugador.nombre}
        
    else:
        return {}
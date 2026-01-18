from equipo.models import Equipo
from usuario.models import Organizador, Administrador, Jugador


def roles_usuario(request):

    usuario =request.user

    if not usuario.is_authenticated:
        return {"is_admin": False, "is_organizador": False,"is_equipo": False, "is_jugador": False}
    
    return {
        "is_admin": Administrador.objects.filter(user=usuario).exists(),
        "is_organizador": Organizador.objects.filter(user=usuario).exists(),
        "is_equipo": Equipo.objects.filter(user=usuario).exists(),
        "is_jugador": Jugador.objects.filter(user=usuario).exists(),
    }
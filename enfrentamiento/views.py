from django.shortcuts import render
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden

from .models import Enfrentamiento
from torneo.models import Torneo, Jornada, Eliminatoria, EliminatoriaGrupos
from gestor.choices import TipoUsuario, TipoTorneo
from torneo.views import tipo_usuario, tiene_permiso





@login_required
def enfrentamientos_torneo(request, torneo_id: int, n_ronda: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user
    if tiene_permiso(usuario, torneo):
        tipo = tipo_usuario(usuario)
        editor = tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR

        enfrentamientos = None
        prev_jornada = True
        sig_jornada = True
        
        if torneo.tipo == TipoTorneo.LIGA:
            if Jornada.objects.filter(torneo=torneo, n_jornada=n_ronda).exists():
                jornada = Jornada.objects.filter(torneo=torneo, n_jornada=n_ronda).first()
                label = _(f'Jornada {n_ronda}')
                if n_ronda-1 < 1:
                    prev_jornada = False
                siguiente = Jornada.objects.filter(torneo=torneo, n_jornada=n_ronda+1).first()
                if not siguiente:
                    sig_jornada = False

                items = Enfrentamiento.objects.filter(jornada=jornada)
                enfrentamientos = {
                    'items': items,
                    'prev_jornada': prev_jornada,
                    'sig_jornada': sig_jornada,
                    'label': label
                }
            else:
                enfrentamientos = {
                    'items': [],
                    'prev_jornada': False,
                    'sig_jornada': False,
                    'label': _(f'Jornada {n_ronda} no existe')
                }

        elif torneo.tipo == TipoTorneo.ELIMINATORIA:
            pass
        elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            pass

        return render(request, 'torneo/enfrentamientos.html', {'torneo': torneo, 'n_ronda': n_ronda, 'enfrentamientos': enfrentamientos, 'editor': editor})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
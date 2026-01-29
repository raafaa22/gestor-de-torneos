from django.shortcuts import render, redirect
from django.db.models import Max
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden

from .models import Enfrentamiento
from torneo.models import Torneo, Jornada, Eliminatoria, EliminatoriaGrupos
from gestor.choices import TipoUsuario, TipoTorneo, TipoRonda
from torneo.views import tipo_usuario, tiene_permiso


RONDAS = [
    TipoRonda.DIECISEISAVOS,
    TipoRonda.OCTAVOS,
    TipoRonda.CUARTOS,
    TipoRonda.SEMIFINAL,
    TipoRonda.FINAL
]


@login_required
def enfrentamientos_torneo(request, torneo_id: int, n_ronda: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user
    if tiene_permiso(usuario, torneo):

        if n_ronda < 1:
            return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=1)
        
        tipo = tipo_usuario(usuario)
        editor = tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR

        enfrentamientos = None
        prev_jornada = True
        sig_jornada = True
        
        if torneo.tipo == TipoTorneo.LIGA:
            jornada = Jornada.objects.filter(torneo=torneo, n_jornada=n_ronda).first()
            selector=[]
            if jornada:
                label = _("Jornada %(n)s") % {"n": n_ronda}

                num_jornadas = (
                    Jornada.objects.filter(torneo=torneo)
                    .aggregate(mx=Max("n_jornada"))
                    .get("mx") or 0
                )


                for i in range(1, num_jornadas + 1):
                    selector.append({
                        'num': i,
                        'label': _("Jornada %(n)s") % {"n": i}
                    })

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
                    'label': label,
                    'selector': selector
                }
            else:
                enfrentamientos = None

        elif torneo.tipo == TipoTorneo.ELIMINATORIA:
            eliminatoria = Eliminatoria.objects.filter(torneo=torneo).first()
            selector=[]
            if eliminatoria:
                secuencia = RONDAS[-eliminatoria.rondas:]
                for i in range(1, eliminatoria.rondas + 1):
                    selector.append({
                        'num': i,
                        'label': secuencia[i-1].label
                    })
                if n_ronda > eliminatoria.rondas:
                    return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=eliminatoria.rondas)
                label = secuencia[n_ronda-1].label
                if n_ronda-1 < 1:
                    prev_jornada = False
                if n_ronda >= eliminatoria.rondas:
                    sig_jornada = False

                items = Enfrentamiento.objects.filter(eliminatoria=eliminatoria, ronda=secuencia[n_ronda-1])
                enfrentamientos = {
                    'items': items,
                    'prev_jornada': prev_jornada,
                    'sig_jornada': sig_jornada,
                    'label': label,
                    'selector': selector
                }
            else:
                enfrentamientos = None
                
        elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            eg = EliminatoriaGrupos.objects.filter(torneo=torneo).first()
            if eg:
                eliminatoria = eg.eliminatoria
                secuencia = RONDAS[-eliminatoria.rondas:]
                selector=[]

                max_jornada = (
                    Jornada.objects.filter(torneo=torneo)
                    .aggregate(mx=Max("n_jornada"))
                    .get("mx") or 0
                )

                total_fases = max_jornada + eliminatoria.rondas

                for i in range(1, total_fases + 1):
                    if i <= max_jornada:
                        label = _("Grupos - Jornada %(n)s") % {"n": i}
                    else:
                        j = i - max_jornada
                        label = _("Playoffs - %(r)s") % {"r": secuencia[j-1].label}

                    selector.append({
                        'num': i,
                        'label': label
                    })

                if n_ronda > total_fases:
                    enfrentamientos = None
                else:
                    prev_jornada = n_ronda > 1
                    sig_jornada = n_ronda < total_fases

                    # ---- FASE DE GRUPOS (JORNADAS) ----
                    if n_ronda <= max_jornada:
                        jornada = Jornada.objects.filter(torneo=torneo, n_jornada=n_ronda).first()
                        if jornada:
                            items = Enfrentamiento.objects.filter(jornada=jornada)

                            label = _("Fase de grupos - Jornada %(n)s") % {"n": n_ronda}

                            enfrentamientos = {
                                "items": items,
                                "prev_jornada": prev_jornada,
                                "sig_jornada": sig_jornada,
                                "label": label,
                                "selector": selector,
                            }
                        else:
                            enfrentamientos = None

                    # ---- (ELIMINATORIA) ----
                    else:
                        ronda_idx = n_ronda - max_jornada

                        tipo_ronda = secuencia[ronda_idx - 1]  

                        items = Enfrentamiento.objects.filter(
                            eliminatoria=eliminatoria,
                            ronda=tipo_ronda
                        )

                        label = _("Playoffs - %(r)s") % {"r": tipo_ronda.label}

                        enfrentamientos = {
                            "items": items,
                            "prev_jornada": prev_jornada,
                            "sig_jornada": sig_jornada,
                            "label": label,
                            "selector": selector,
                        }
            else:
                enfrentamientos = None
            
        else:
            enfrentamientos = None


        
        return render(request, 'torneo/enfrentamientos.html', {'torneo': torneo, 'n_ronda': n_ronda, 'enfrentamientos': enfrentamientos, 'editor': editor})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    

@login_required
def detalle_enfrentamiento(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
    return render(request, 'enfrentamientos/editar.html', {'torneo': torneo, 'n_ronda': n_ronda, 'enfrentamiento': enfrentamiento})

@login_required
def editar_enfrentamiento(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
    return render(request, 'enfrentamientos/editar.html', {'torneo': torneo, 'n_ronda': n_ronda, 'enfrentamiento': enfrentamiento})
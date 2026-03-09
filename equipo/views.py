from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.db import transaction

from .models import Equipo
from enfrentamiento.models import Enfrentamiento
from torneo.models import Torneo, TorneoEquipo, Clasificacion, Eliminatoria
from gestor.choices import TipoTorneo, TipoUsuario, Deporte
from torneo.views import tipo_usuario
from enfrentamiento.libs import RONDAS, baja_equipo_torneo


@login_required
def dashboard(request):
    usuario = request.user
    equipo = Equipo.objects.filter(user=usuario).first()

    if equipo is None or tipo_usuario(usuario) != TipoUsuario.EQUIPO:
        return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
    
    datos = []

    torneo_equipo = TorneoEquipo.objects.filter(equipo=equipo)
    for te in torneo_equipo:
        id = te.torneo.id
        nombre = te.torneo.nombre
        tipo = te.torneo.tipo
        if tipo == TipoTorneo.LIGA or tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            clasificacion = Clasificacion.objects.filter(torneo_equipo=te).first()
            datos.append({
                'id': id,
                'nombre': nombre,
                'tipo': TipoTorneo(tipo).label,
                'estado': "%(n)sº" % {'n': clasificacion.posicion},
                'anotacion_favor': clasificacion.anotacion_favor,
                'anotacion_contra': clasificacion.anotacion_contra
            })

        elif tipo == TipoTorneo.ELIMINATORIA:
            eliminatoria = Eliminatoria.objects.filter(torneo=te.torneo).first()
            rondas_torneo = RONDAS[-eliminatoria.rondas:]
            ronda_actual = rondas_torneo[0].label
            anotacion_favor = 0
            anotacion_contra = 0
            for ronda in rondas_torneo:
                enfrentamiento_local = Enfrentamiento.objects.filter(eliminatoria__torneo=te.torneo, ronda=ronda, equipo_local=equipo).first()
                if enfrentamiento_local is not None:
                    ronda_actual = ronda.label
                    if te.torneo.deporte == Deporte.PADEL:
                        anotacion_favor += (enfrentamiento_local.juegos_local_1 or 0) + (enfrentamiento_local.juegos_local_2 or 0) + (enfrentamiento_local.juegos_local_3 or 0)
                        anotacion_contra += (enfrentamiento_local.juegos_visitante_1 or 0) + (enfrentamiento_local.juegos_visitante_2 or 0) + (enfrentamiento_local.juegos_visitante_3 or 0)
                    else:
                        anotacion_favor += enfrentamiento_local.anotacion_local or 0
                        anotacion_contra += enfrentamiento_local.anotacion_visitante or 0
                else:
                    enfrentamiento_visitante = Enfrentamiento.objects.filter(eliminatoria__torneo=te.torneo, ronda=ronda, equipo_visitante=equipo).first()
                    if enfrentamiento_visitante is not None:
                        ronda_actual = ronda.label
                        if te.torneo.deporte == Deporte.PADEL:
                            anotacion_favor += (enfrentamiento_visitante.juegos_visitante_1 or 0) + (enfrentamiento_visitante.juegos_visitante_2 or 0) + (enfrentamiento_visitante.juegos_visitante_3 or 0)
                            anotacion_contra += (enfrentamiento_visitante.juegos_local_1 or 0) + (enfrentamiento_visitante.juegos_local_2 or 0) + (enfrentamiento_visitante.juegos_local_3 or 0)
                        else:
                            anotacion_favor += enfrentamiento_visitante.anotacion_visitante or 0
                            anotacion_contra += enfrentamiento_visitante.anotacion_local or 0
                    else:
                        break
            
            datos.append({
                'id': id,
                'nombre': nombre,
                'tipo': TipoTorneo(tipo).label,
                'estado': ronda_actual,
                'anotacion_favor': anotacion_favor,
                'anotacion_contra': anotacion_contra
            })
        

    return render(request, 'equipo/dashboard.html', {'torneos': datos, 'equipo': equipo})



@login_required
@require_POST
@transaction.atomic
def dar_baja_torneo(request, torneo_id):
    usuario = request.user
    equipo = Equipo.objects.filter(user=usuario).first()

    if equipo is None or tipo_usuario(usuario) != TipoUsuario.EQUIPO:
        return HttpResponseForbidden("No tienes permiso para acceder a esta página.")

    torneo = get_object_or_404(Torneo, id=torneo_id)
    if not TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).exists():
        return HttpResponseForbidden("No estás inscrito en este torneo.")

    baja_equipo_torneo(torneo, equipo)

    return redirect('equipo:dashboard')


def listado_torneos_inscribir(request, equipo_id):
    return render(request, 'equipo/listado_torneos.html')

def listado_jugadores(request, equipo_id):
    return render(request, 'equipo/listado_jugadores.html')
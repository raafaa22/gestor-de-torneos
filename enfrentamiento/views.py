from django.shortcuts import render, redirect
from django.db.models import Max, F, ExpressionWrapper, IntegerField
from math import log2
from django.db import transaction
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, HttpResponse

from equipo.models import Equipo

from .models import Enfrentamiento, EstadisticasEnfrentamiento, GuardadoEnfrentamiento
from .forms import EstadisticasEnfrentamientoForm
from estadisticas.models import EstadisticasBaloncesto, EstadisticasFutbol
from torneo.models import Torneo, Jornada, Eliminatoria, EliminatoriaGrupos, Clasificacion, TorneoEquipo
from gestor.choices import TipoUsuario, TipoTorneo, TipoRonda, EstadisticaFutbol, EstadisticaBaloncesto, Deporte
from usuario.models import Jugador
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

    if tiene_permiso(request.user, torneo):
        jugadores_local = Jugador.objects.filter(equipo=enfrentamiento.equipo_local)
        jugadores_visitante = Jugador.objects.filter(equipo=enfrentamiento.equipo_visitante)

        clasificacion_local = None
        clasificacion_visitante = None

        if torneo.tipo == TipoTorneo.LIGA or torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            equipo_local = TorneoEquipo.objects.filter(torneo=torneo, equipo=enfrentamiento.equipo_local).first()
            clasificacion_local = Clasificacion.objects.filter(torneo_equipo=equipo_local).first()
            equipo_visitante = TorneoEquipo.objects.filter(torneo=torneo, equipo=enfrentamiento.equipo_visitante).first()
            clasificacion_visitante = Clasificacion.objects.filter(torneo_equipo=equipo_visitante).first()

        estadisticas_local = GuardadoEnfrentamiento.objects.filter(enfrentamiento=enfrentamiento, jugador__equipo=enfrentamiento.equipo_local)
        estadisticas_visitante = GuardadoEnfrentamiento.objects.filter(enfrentamiento=enfrentamiento, jugador__equipo=enfrentamiento.equipo_visitante)
        contexto = {
            'jugadores_local': jugadores_local,
            'jugadores_visitante': jugadores_visitante,
            'clasificacion_local': clasificacion_local,
            'clasificacion_visitante': clasificacion_visitante,
            'estadisticas_local': estadisticas_local,
            'estadisticas_visitante': estadisticas_visitante
        }
    

        return render(request, 'enfrentamientos/detalle.html', {'torneo': torneo, 'n_ronda': n_ronda, 'enfrentamiento': enfrentamiento, 'contexto': contexto})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

@login_required
def editar_enfrentamiento(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int):
    usuario = request.user
    torneo = get_object_or_404(Torneo, id=torneo_id)
    enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
    tipo = tipo_usuario(usuario)

    if tiene_permiso(usuario, torneo) and (tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR):
        estadisticas_local = None
        estadisticas_visitante = None
        estadisticas = EstadisticasEnfrentamiento.objects.filter(enfrentamiento=enfrentamiento)
        if estadisticas.exists():
            estadisticas_local = estadisticas.filter(jugador__equipo=enfrentamiento.equipo_local)
            estadisticas_visitante = estadisticas.filter(jugador__equipo=enfrentamiento.equipo_visitante)

        form_local = EstadisticasEnfrentamientoForm(torneo=torneo, equipo=enfrentamiento.equipo_local, enfrentamiento=enfrentamiento)
        form_visitante = EstadisticasEnfrentamientoForm(torneo=torneo, equipo=enfrentamiento.equipo_visitante, enfrentamiento=enfrentamiento)

        return render(request, 'enfrentamientos/editar.html', {'torneo': torneo, 'n_ronda': n_ronda, 'enfrentamiento': enfrentamiento, 'estadisticas_local': estadisticas_local, 'estadisticas_visitante': estadisticas_visitante, 'form_local': form_local, 'form_visitante': form_visitante})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

@login_required
@require_POST
def guardar_estadistica(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int, equipo_id: int):
    usuario = request.user

    tipo_usu = tipo_usuario(usuario)

    if tipo_usu == TipoUsuario.ORGANIZADOR or tipo_usu == TipoUsuario.ADMINISTRADOR:
        
        torneo = get_object_or_404(Torneo, id=torneo_id)
        enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
        equipo=get_object_or_404(Equipo, id=equipo_id)

        if equipo != enfrentamiento.equipo_local and equipo != enfrentamiento.equipo_visitante:
            return HttpResponseForbidden( _("El equipo no participa en este enfrentamiento.") )
        
        form = EstadisticasEnfrentamientoForm(request.POST, torneo=torneo, equipo=equipo, enfrentamiento=enfrentamiento)

        if form.is_valid():

            tipo = form.cleaned_data['tipo']
            cantidad = form.cleaned_data['cantidad']

            if tipo == EstadisticaFutbol.GOLES or tipo == EstadisticaBaloncesto.PUNTOS:
                if equipo == enfrentamiento.equipo_local:
                    enfrentamiento.anotacion_local = (enfrentamiento.anotacion_local or 0) + cantidad
                else:
                    enfrentamiento.anotacion_visitante = (enfrentamiento.anotacion_visitante or 0) + cantidad
                breakpoint()
                enfrentamiento.save()
            
            form.save()

            return redirect('enfrentamientos:editar_enfrentamiento', torneo_id=torneo_id, n_ronda=n_ronda, enfrentamiento_id=enfrentamiento_id)
        else:
            estadisticas_local = EstadisticasEnfrentamiento.objects.filter(
                enfrentamiento=enfrentamiento, jugador__equipo=enfrentamiento.equipo_local
            )
            estadisticas_visitante = EstadisticasEnfrentamiento.objects.filter(
                enfrentamiento=enfrentamiento, jugador__equipo=enfrentamiento.equipo_visitante
            )

            
            form_local = form if equipo_id == enfrentamiento.equipo_local_id else EstadisticasEnfrentamientoForm(
                torneo=torneo, equipo=enfrentamiento.equipo_local, enfrentamiento=enfrentamiento
            )
            form_visitante = form if equipo_id == enfrentamiento.equipo_visitante_id else EstadisticasEnfrentamientoForm(
                torneo=torneo, equipo=enfrentamiento.equipo_visitante, enfrentamiento=enfrentamiento
            )

        return render(request, "enfrentamientos/editar.html", {
            "torneo": torneo,
            "n_ronda": n_ronda,
            "enfrentamiento": enfrentamiento,
            "form_local": form_local,
            "form_visitante": form_visitante,
            "estadisticas_local": estadisticas_local,
            "estadisticas_visitante": estadisticas_visitante,
        })

    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

    

    

@login_required
def borrar_estadistica(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int, estadistica_id: int):
    usuario = request.user

    tipo_usu = tipo_usuario(usuario)

    if tipo_usu == TipoUsuario.ORGANIZADOR or tipo_usu == TipoUsuario.ADMINISTRADOR:

        enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
        estadistica = get_object_or_404(EstadisticasEnfrentamiento, id=estadistica_id)
        tipo = estadistica.estadistica_futbol or estadistica.estadistica_baloncesto
        cantidad = estadistica.cantidad
        equipo = estadistica.jugador.equipo

        if tipo == EstadisticaFutbol.GOLES or tipo == EstadisticaBaloncesto.PUNTOS:
            if equipo == enfrentamiento.equipo_local:
                enfrentamiento.anotacion_local = enfrentamiento.anotacion_local - cantidad
            else:
                enfrentamiento.anotacion_visitante = enfrentamiento.anotacion_visitante - cantidad
            enfrentamiento.save()

        estadistica.delete()

        return redirect('enfrentamientos:editar_enfrentamiento', torneo_id=torneo_id, n_ronda=n_ronda, enfrentamiento_id=enfrentamiento_id)
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )


@transaction.atomic
def actualizar_clasificacion(torneo: Torneo, enfrentamiento: Enfrentamiento):
    eq_local = TorneoEquipo.objects.filter(torneo=torneo, equipo=enfrentamiento.equipo_local).first()
    eq_visitante = TorneoEquipo.objects.filter(torneo=torneo, equipo=enfrentamiento.equipo_visitante).first()

    clasif_local = Clasificacion.objects.filter(torneo_equipo=eq_local).first()
    clasif_visitante = Clasificacion.objects.filter(torneo_equipo=eq_visitante).first()
    puntos_ganador = 0
    puntos_perdedor = 0
    
    if torneo.deporte == Deporte.FUTBOL:
        puntos_ganador = 3
    elif torneo.deporte == Deporte.BALONCESTO:
        puntos_ganador = 2
        puntos_perdedor = 1
    else:
        puntos_ganador = 1

    ganador = None
    perdedor = None

    if enfrentamiento.ganador == enfrentamiento.equipo_local:
        ganador = clasif_local
        perdedor = clasif_visitante
    elif enfrentamiento.ganador == enfrentamiento.equipo_visitante:
        ganador = clasif_visitante
        perdedor = clasif_local
    else:
        if torneo.deporte == Deporte.FUTBOL:
            clasif_local.puntos += 1
            clasif_visitante.puntos += 1
            clasif_local.empates += 1
            clasif_visitante.empates += 1
    
    if ganador and perdedor:
        ganador.puntos += puntos_ganador
        ganador.victorias += 1
        perdedor.puntos += puntos_perdedor
        perdedor.derrotas += 1

    if torneo.deporte == Deporte.PADEL:
        clasif_local.anotacion_favor += (enfrentamiento.juegos_local_1 or 0) + (enfrentamiento.juegos_local_2 or 0) + (enfrentamiento.juegos_local_3 or 0)
        clasif_local.anotacion_contra += (enfrentamiento.juegos_visitante_1 or 0) + (enfrentamiento.juegos_visitante_2 or 0) + (enfrentamiento.juegos_visitante_3 or 0)
        clasif_visitante.anotacion_favor += (enfrentamiento.juegos_visitante_1 or 0) + (enfrentamiento.juegos_visitante_2 or 0) + (enfrentamiento.juegos_visitante_3 or 0)
        clasif_visitante.anotacion_contra += (enfrentamiento.juegos_local_1 or 0) + (enfrentamiento.juegos_local_2 or 0) + (enfrentamiento.juegos_local_3 or 0)
    else:
        clasif_local.anotacion_favor += enfrentamiento.anotacion_local or 0
        clasif_local.anotacion_contra += enfrentamiento.anotacion_visitante or 0
        clasif_visitante.anotacion_favor += enfrentamiento.anotacion_visitante or 0
        clasif_visitante.anotacion_contra += enfrentamiento.anotacion_local or 0

    clasif_local.save()
    clasif_visitante.save()
    
    
    if torneo.tipo == TipoTorneo.LIGA:
        equipos = Clasificacion.objects.filter(torneo_equipo__torneo=torneo).annotate(
            dif=ExpressionWrapper(F('anotacion_favor') - F('anotacion_contra'), output_field=IntegerField())
        ).order_by('-puntos', '-victorias', '-dif', 'derrotas', '-anotacion_favor', 'anotacion_contra')
        
        
        for i, equipo in enumerate(equipos):
            equipo.posicion = i + 1
            equipo.save()

    elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        grupo = Clasificacion.objects.filter(torneo_equipo=eq_local).first().grupo
        equipos = Clasificacion.objects.filter(torneo_equipo__torneo=torneo, grupo=grupo).annotate(
            dif=ExpressionWrapper(F('anotacion_favor') - F('anotacion_contra'), output_field=IntegerField())
        ).order_by('-puntos', '-victorias', '-dif', 'derrotas', '-anotacion_favor', 'anotacion_contra')

        for i, equipo in enumerate(equipos):
            equipo.posicion = i + 1
            equipo.save()

    
@transaction.atomic
def actualizar_eliminatoria(enfrentamiento: Enfrentamiento):
    if enfrentamiento.ganador is not None:
        siguiente = Enfrentamiento.objects.filter(eliminatoria=enfrentamiento.eliminatoria, prev_local=enfrentamiento).first()
        if siguiente is not None:
            siguiente.equipo_local = enfrentamiento.ganador
            siguiente.save()
        else:
            siguiente = Enfrentamiento.objects.filter(eliminatoria=enfrentamiento.eliminatoria, prev_visitante=enfrentamiento).first()
            if siguiente is not None:
                siguiente.equipo_visitante = enfrentamiento.ganador
                siguiente.save()
            else:
                return HttpResponse( _("No se encontró el siguiente enfrentamiento para actualizar."), status=400 )
    else:
        return HttpResponse( _("No se puede actualizar la eliminatoria sin un ganador definido."), status=400 )

@transaction.atomic
def actualizar_estadisticas_generales(torneo: Torneo, enfrentamiento: Enfrentamiento):
    estadisticas_guardadas = GuardadoEnfrentamiento.objects.filter(enfrentamiento=enfrentamiento)
    estadisticas_pendientes = EstadisticasEnfrentamiento.objects.filter(enfrentamiento=enfrentamiento)

    if estadisticas_guardadas.exists():
        for existe in estadisticas_guardadas:
            if not estadisticas_pendientes.filter(
                jugador=existe.jugador,
                estadistica_futbol=existe.estadistica_futbol,
                estadistica_baloncesto=existe.estadistica_baloncesto
            ).exists():
                if existe.estadistica_futbol:
                    general = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=existe.jugador).first()

                    if existe.estadistica_futbol == EstadisticaFutbol.GOLES:
                        general.goles -= existe.cantidad
                    elif existe.estadistica_futbol == EstadisticaFutbol.ASISTENCIAS:
                        general.asistencias -= existe.cantidad
                
                elif existe.estadistica_baloncesto:
                    general = EstadisticasBaloncesto.objects.filter(torneo=torneo, jugador=existe.jugador).first()

                    if existe.estadistica_baloncesto == EstadisticaBaloncesto.PUNTOS:
                        general.puntos -= existe.cantidad
                    elif existe.estadistica_baloncesto == EstadisticaBaloncesto.ASISTENCIAS:
                        general.asistencias -= existe.cantidad
                    elif existe.estadistica_baloncesto == EstadisticaBaloncesto.REBOTES:
                        general.rebotes -= existe.cantidad

                general.save()
                existe.delete()
            

    for estadistica in estadisticas_pendientes:
        guardada = estadisticas_guardadas.filter(
            jugador=estadistica.jugador,
            estadistica_futbol=estadistica.estadistica_futbol,
            estadistica_baloncesto=estadistica.estadistica_baloncesto
        ).first()

        diferencia = 0
        if guardada is not None:
            if guardada.cantidad != estadistica.cantidad:
                diferencia = estadistica.cantidad - guardada.cantidad
                guardada.cantidad = estadistica.cantidad
                guardada.save()
        else:
            diferencia = estadistica.cantidad
            GuardadoEnfrentamiento.objects.create(
                enfrentamiento=enfrentamiento,
                jugador=estadistica.jugador,
                estadistica_futbol=estadistica.estadistica_futbol,
                estadistica_baloncesto=estadistica.estadistica_baloncesto,
                cantidad=estadistica.cantidad
            )

        if diferencia != 0:
            if estadistica.estadistica_futbol:
                general = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=estadistica.jugador).first()

                if estadistica.estadistica_futbol == EstadisticaFutbol.GOLES:
                    general.goles += diferencia
                elif estadistica.estadistica_futbol == EstadisticaFutbol.ASISTENCIAS:
                    general.asistencias += diferencia
                
            
            elif estadistica.estadistica_baloncesto:
                general = EstadisticasBaloncesto.objects.filter(torneo=torneo, jugador=estadistica.jugador).first()

                if estadistica.estadistica_baloncesto == EstadisticaBaloncesto.PUNTOS:
                    general.puntos += diferencia
                elif estadistica.estadistica_baloncesto == EstadisticaBaloncesto.ASISTENCIAS:
                    general.asistencias += diferencia
                elif estadistica.estadistica_baloncesto == EstadisticaBaloncesto.REBOTES:
                    general.rebotes += diferencia
            
            general.save()


def sig_potencia_2(n: int) -> int:
    return 1 << (n - 1).bit_length()

def crear_eliminatoria_tras_liga(torneo: Torneo):
    espacios = sig_potencia_2(torneo.n_equipos_playoffs)
    partidos_ronda = espacios // 2
    directos = espacios - torneo.n_equipos_playoffs
    rondas = int(log2(espacios))

    if torneo.tipo == TipoTorneo.LIGA:
        clasificados = Clasificacion.objects.filter(torneo_equipo__torneo=torneo, posicion__lte=torneo.n_equipos_playoffs).order_by('posicion')
        eliminatoria = Eliminatoria.objects.create(torneo=torneo, rondas=rondas)

    elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        eliminatoria_grupos = EliminatoriaGrupos.objects.filter(torneo=torneo).first()
        clasificados = Clasificacion.objects.filter(torneo_equipo__torneo=torneo, posicion__lte=eliminatoria_grupos.n_clasificados_grupo).order_by('posicion', '-puntos', '-victorias', 'derrotas', '-anotacion_favor', 'anotacion_contra')
        eliminatoria = eliminatoria_grupos.eliminatoria


    enfrentamientos = []

    rondas_torneo = RONDAS[-rondas:]

    for i in range(partidos_ronda):
        if i < directos:
            enfrentamientos.append(
                Enfrentamiento.objects.create(ronda=rondas_torneo[0], eliminatoria=eliminatoria, equipo_local=clasificados[i].torneo_equipo.equipo, equipo_visitante=None)
            )
        else:
            enfrentamientos.append(
                Enfrentamiento.objects.create(
                    ronda=rondas_torneo[0],
                    eliminatoria=eliminatoria,
                    equipo_local=clasificados[i].torneo_equipo.equipo,
                    equipo_visitante=clasificados[espacios - i - 1].torneo_equipo.equipo
                )
            )

    for i in range(1, rondas):
        guardado = enfrentamientos.copy()
        enfrentamientos = []
        for j in range(partidos_ronda//2):
            enfrentamientos.append(
                Enfrentamiento.objects.create(
                    ronda=rondas_torneo[i],
                    eliminatoria=eliminatoria,
                    prev_local=guardado[j],
                    prev_visitante=guardado[partidos_ronda - j - 1]
                )
            )

        partidos_ronda = partidos_ronda // 2

    
    enf_no_validos = Enfrentamiento.objects.filter(eliminatoria=eliminatoria, equipo_local__isnull=False, equipo_visitante__isnull=True, ronda=rondas_torneo[0])
    for enf in enf_no_validos:
        siguiente = Enfrentamiento.objects.filter(prev_local=enf).first()
        if siguiente:
            siguiente.equipo_local = enf.equipo_local
            siguiente.save()
        else:
            siguiente = Enfrentamiento.objects.filter(prev_visitante=enf).first()
            if siguiente:
                siguiente.equipo_visitante = enf.equipo_local
                siguiente.save()
        
        enf.delete()         


@login_required
@require_POST
def guardar_enfrentamiento(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int):
    usuario = request.user

    tipo_usu = tipo_usuario(usuario)

    if tipo_usu == TipoUsuario.ORGANIZADOR or tipo_usu == TipoUsuario.ADMINISTRADOR:
        torneo = get_object_or_404(Torneo, id=torneo_id)
        enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
        
        if torneo.deporte == Deporte.PADEL:
            enfrentamiento.juegos_local_1 = int(request.POST.get('juegos_local_1'))
            enfrentamiento.juegos_visitante_1 = int(request.POST.get('juegos_visitante_1'))
            enfrentamiento.juegos_local_2 = int(request.POST.get('juegos_local_2'))
            enfrentamiento.juegos_visitante_2 = int(request.POST.get('juegos_visitante_2'))
            enfrentamiento.juegos_local_3 = int(request.POST.get('juegos_local_3'))
            enfrentamiento.juegos_visitante_3 = int(request.POST.get('juegos_visitante_3'))
            

            sets_local = 0
            sets_visitante = 0

            if enfrentamiento.juegos_local_1 is not None and enfrentamiento.juegos_visitante_1 is not None:
                if enfrentamiento.juegos_local_1 != enfrentamiento.juegos_visitante_1:
                    if enfrentamiento.juegos_local_1 > enfrentamiento.juegos_visitante_1:
                        sets_local += 1
                    else:
                        sets_visitante += 1
                    
                    if enfrentamiento.juegos_local_2 is not None and enfrentamiento.juegos_visitante_2 is not None:
                        if enfrentamiento.juegos_local_2 != enfrentamiento.juegos_visitante_2:
                            if enfrentamiento.juegos_local_2 > enfrentamiento.juegos_visitante_2:
                                sets_local += 1
                                if sets_local == 2:
                                    enfrentamiento.ganador = enfrentamiento.equipo_local
                            else:
                                sets_visitante += 1
                                if sets_visitante == 2:
                                    enfrentamiento.ganador = enfrentamiento.equipo_visitante
                            
                            if sets_local == sets_visitante:
                                if enfrentamiento.juegos_local_3 is not None and enfrentamiento.juegos_visitante_3 is not None:
                                    if enfrentamiento.juegos_local_3 != enfrentamiento.juegos_visitante_3:
                                        if enfrentamiento.juegos_local_3 > enfrentamiento.juegos_visitante_3:
                                            enfrentamiento.ganador = enfrentamiento.equipo_local
                                        else:
                                            enfrentamiento.ganador = enfrentamiento.equipo_visitante
                                    else:
                                        return HttpResponse( _("El tercer set no puede terminar en empate."), status=400 )
                                else:
                                    return HttpResponse( _("Debe introducir el resultado del tercer set."), status=400 )
                        else:
                            return HttpResponse( _("En pádel no puede haber empates."), status=400 )
                    else:
                        return HttpResponse( _("Debe introducir el resultado del segundo set."), status=400 )
                else:
                    return HttpResponse( _("En pádel no puede haber empates."), status=400 )
            else:
                return HttpResponse( _("Debe introducir el resultado del primer set."), status=400 )
            
        else:
            enfrentamiento.anotacion_local = int(request.POST.get('anotacion_local'))
            enfrentamiento.anotacion_visitante = int(request.POST.get('anotacion_visitante'))


            if enfrentamiento.anotacion_local is not None and enfrentamiento.anotacion_visitante is not None:
                if enfrentamiento.anotacion_local > enfrentamiento.anotacion_visitante:
                    enfrentamiento.ganador = enfrentamiento.equipo_local
                elif enfrentamiento.anotacion_visitante > enfrentamiento.anotacion_local:
                    enfrentamiento.ganador = enfrentamiento.equipo_visitante
                else:
                    if torneo.deporte == Deporte.BALONCESTO:
                        return HttpResponse( _("En baloncesto no puede haber empates."), status=400 )
            else:
                enfrentamiento.ganador = None

        enfrentamiento.save()
        
        if torneo.tipo == TipoTorneo.LIGA:
            if enfrentamiento.jornada is not None:
                actualizar_clasificacion(torneo, enfrentamiento)
        
                max_jornada = (
                    Jornada.objects.filter(torneo=torneo)
                    .aggregate(mx=Max("n_jornada"))
                    .get("mx") or 0
                )
                if enfrentamiento.jornada.n_jornada == max_jornada:
                    equipos_torneo = TorneoEquipo.objects.filter(torneo=torneo)
                    clas_equipos = Clasificacion.objects.filter(torneo_equipo__in=equipos_torneo)

                    liga_terminada = True

                    for equipo in clas_equipos:
                        if equipo.partidos_jugados < max_jornada:
                            liga_terminada = False
                            break
                    
                    if liga_terminada:
                        if torneo.playoffs:
                            crear_eliminatoria_tras_liga(torneo)
                        else:
                            clas_ganador = clas_equipos.filter(posicion=1).first()
                            torneo.ganador = clas_ganador.torneo_equipo.equipo
                            torneo.save()
            else:
                if enfrentamiento.ronda == TipoRonda.FINAL:
                    torneo.ganador = enfrentamiento.ganador
                    torneo.save()
                        

        elif torneo.tipo == TipoTorneo.ELIMINATORIA:
            if enfrentamiento.ronda == TipoRonda.FINAL:
                torneo.ganador = enfrentamiento.ganador
                torneo.save()
            else:
                actualizar_eliminatoria(enfrentamiento)
        elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            if enfrentamiento.jornada is not None:
                actualizar_clasificacion(torneo, enfrentamiento)
                max_jornada = (
                    Jornada.objects.filter(torneo=torneo)
                    .aggregate(mx=Max("n_jornada"))
                    .get("mx") or 0
                )
                if enfrentamiento.jornada.n_jornada == max_jornada:
                    equipos_torneo = TorneoEquipo.objects.filter(torneo=torneo)
                    clas_equipos = Clasificacion.objects.filter(torneo_equipo__in=equipos_torneo)

                    fase_grupos_terminada = True

                    for equipo in clas_equipos:
                        if equipo.partidos_jugados < max_jornada:
                            fase_grupos_terminada = False
                            break
                    
                    if fase_grupos_terminada:
                        crear_eliminatoria_tras_liga(torneo)
            else:
                if enfrentamiento.ronda == TipoRonda.FINAL:
                    torneo.ganador = enfrentamiento.ganador
                    torneo.save()
                else:
                    actualizar_eliminatoria(enfrentamiento)

        if torneo.deporte == Deporte.FUTBOL:
            portero_local = Jugador.objects.filter(equipo=enfrentamiento.equipo_local, es_portero=True).first()
            portero_visitante = Jugador.objects.filter(equipo=enfrentamiento.equipo_visitante, es_portero=True).first()

            if portero_local:
                estadisticas_portero_local = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=portero_local).first()
                estadisticas_portero_local.goles_contra += enfrentamiento.anotacion_visitante or 0
                estadisticas_portero_local.save()
            
            if portero_visitante:
                estadisticas_portero_visitante = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=portero_visitante).first()
                estadisticas_portero_visitante.goles_contra += enfrentamiento.anotacion_local or 0
                estadisticas_portero_visitante.save()

        actualizar_estadisticas_generales(torneo, enfrentamiento)

        return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=n_ronda)
                    
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    



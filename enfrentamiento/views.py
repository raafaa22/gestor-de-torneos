from django.shortcuts import render, redirect
from django.db.models import Max
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, HttpResponse

from equipo.models import Equipo

from .models import Enfrentamiento, EstadisticasEnfrentamiento, GuardadoEnfrentamiento
from .forms import EstadisticasEnfrentamientoForm
from torneo.models import Torneo, Jornada, Eliminatoria, EliminatoriaGrupos, Clasificacion, TorneoEquipo
from gestor.choices import TipoUsuario, TipoTorneo, TipoRonda, EstadisticaFutbol, EstadisticaBaloncesto, Deporte, Nivel
from usuario.models import Jugador
from torneo.views import tipo_usuario, tiene_permiso

from .libs import *


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
            eliminatoria = Eliminatoria.objects.filter(torneo=torneo).first()
            num_jornadas = (
                Jornada.objects.filter(torneo=torneo)
                .aggregate(mx=Max("n_jornada"))
                .get("mx") or 0
            )

            if eliminatoria and eliminatoria.rondas > 0:
                secuencia = RONDAS[-eliminatoria.rondas:]
                total_fases = num_jornadas + eliminatoria.rondas
            else:
                secuencia = []
                total_fases = num_jornadas

            selector = []
            for i in range(1, total_fases + 1):
                if i <= num_jornadas:
                    label = _("Jornada %(n)s") % {"n": i}
                else:
                    j = i - num_jornadas
                    label = secuencia[j-1].label
                selector.append({'num': i, 'label': label})

            if total_fases > 0 and n_ronda > total_fases:
                return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=total_fases)
            elif total_fases > 0:
                prev_jornada = n_ronda > 1
                sig_jornada = n_ronda < total_fases

                # ---- FASE DE LIGA ----
                if n_ronda <= num_jornadas:
                    jornada = Jornada.objects.filter(torneo=torneo, n_jornada=n_ronda).first()
                    if jornada:
                        items = Enfrentamiento.objects.filter(jornada=jornada)
                        label = _("Jornada %(n)s") % {"n": n_ronda}
                        enfrentamientos = {
                            'items': items,
                            'prev_jornada': prev_jornada,
                            'sig_jornada': sig_jornada,
                            'label': label,
                            'selector': selector
                        }
                    else:
                        enfrentamientos = None
                # ---- PLAYOFFS (ELIMINATORIA) ----
                else:
                    ronda_idx = n_ronda - num_jornadas
                    tipo_ronda = secuencia[ronda_idx - 1]

                    items = Enfrentamiento.objects.filter(
                        eliminatoria=eliminatoria,
                        ronda=tipo_ronda
                    )
                    label = tipo_ronda.label

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
            if eliminatoria and eliminatoria.rondas > 0:
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
            max_jornada = (
                Jornada.objects.filter(torneo=torneo)
                .aggregate(mx=Max("n_jornada"))
                .get("mx") or 0
            )

            if eg:
                eliminatoria = eg.eliminatoria
                if eliminatoria:
                    secuencia = RONDAS[-eliminatoria.rondas:]
                    selector=[]


                    total_fases = max_jornada + eliminatoria.rondas

                    for i in range(1, total_fases + 1):
                        if i <= max_jornada:
                            label = _("Grupos - Jornada %(n)s") % {"n": i}
                        else:
                            j = i - max_jornada
                            label = secuencia[j-1].label

                        selector.append({
                            'num': i,
                            'label': label
                        })

                    if total_fases > 0 and n_ronda > total_fases:
                        return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=total_fases)
                    elif total_fases > 0:
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

                            label =  tipo_ronda.label

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
                    total_fases = max_jornada

                    selector = []

                    for i in range(1, total_fases + 1):
                        selector.append({
                            'num': i,
                            'label': _("Grupos - Jornada %(n)s") % {"n": i}
                        })


                    if total_fases > 0 and n_ronda > total_fases:
                        return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=total_fases)
                    elif total_fases > 0:
                        prev_jornada = n_ronda > 1
                        sig_jornada = n_ronda < total_fases

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
                    else:
                        enfrentamientos = None
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

    if enfrentamiento.equipo_local is None or enfrentamiento.equipo_visitante is None:
        return HttpResponse( _("No se pueden editar las estadísticas de un enfrentamiento sin ambos equipos asignados."), status=400 )

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


  


@login_required
@require_POST
def guardar_enfrentamiento(request, torneo_id: int, n_ronda: int, enfrentamiento_id: int):
    usuario = request.user

    tipo_usu = tipo_usuario(usuario)

    if tipo_usu == TipoUsuario.ORGANIZADOR or tipo_usu == TipoUsuario.ADMINISTRADOR:
        torneo = get_object_or_404(Torneo, id=torneo_id)
        enfrentamiento = get_object_or_404(Enfrentamiento, id=enfrentamiento_id)
        
        MAX_SCORE = 9999

        if torneo.deporte == Deporte.PADEL:
            juegos_keys = [
                'juegos_local_1', 'juegos_visitante_1',
                'juegos_local_2', 'juegos_visitante_2',
                'juegos_local_3', 'juegos_visitante_3',
            ]
            juegos_raw = {k: request.POST.get(k, '').strip() for k in juegos_keys}

            # Si todos los campos están vacíos, reseteamos el enfrentamiento
            # (dejamos que la lógica post-save recalcule clasificación).
            if all(v == '' for v in juegos_raw.values()):
                enfrentamiento.juegos_local_1 = None
                enfrentamiento.juegos_visitante_1 = None
                enfrentamiento.juegos_local_2 = None
                enfrentamiento.juegos_visitante_2 = None
                enfrentamiento.juegos_local_3 = None
                enfrentamiento.juegos_visitante_3 = None
                enfrentamiento.ganador = None
            else:
                try:
                    juegos_local_1    = int(juegos_raw['juegos_local_1'] or 0)
                    juegos_visitante_1 = int(juegos_raw['juegos_visitante_1'] or 0)
                    juegos_local_2    = int(juegos_raw['juegos_local_2'] or 0)
                    juegos_visitante_2 = int(juegos_raw['juegos_visitante_2'] or 0)
                    juegos_local_3    = int(juegos_raw['juegos_local_3'] or 0)
                    juegos_visitante_3 = int(juegos_raw['juegos_visitante_3'] or 0)
                except (ValueError, TypeError):
                    return HttpResponse(_("Los valores de juegos introducidos no son válidos."), status=400)

                if any(v < 0 for v in [
                    juegos_local_1, juegos_visitante_1,
                    juegos_local_2, juegos_visitante_2,
                    juegos_local_3, juegos_visitante_3,
                ]):
                    return HttpResponse(_("Los juegos no pueden ser negativos."), status=400)

                if any(v > 7 for v in [
                    juegos_local_1, juegos_visitante_1,
                    juegos_local_2, juegos_visitante_2,
                    juegos_local_3, juegos_visitante_3,
                ]):
                    return HttpResponse(_("Los juegos de un set no pueden superar 7."), status=400)

                enfrentamiento.juegos_local_1    = juegos_local_1
                enfrentamiento.juegos_visitante_1 = juegos_visitante_1
                enfrentamiento.juegos_local_2    = juegos_local_2
                enfrentamiento.juegos_visitante_2 = juegos_visitante_2
                enfrentamiento.juegos_local_3    = juegos_local_3
                enfrentamiento.juegos_visitante_3 = juegos_visitante_3


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
            anotacion_local_raw = request.POST.get('anotacion_local', '').strip()
            anotacion_visitante_raw = request.POST.get('anotacion_visitante', '').strip()

            if anotacion_local_raw == '' and anotacion_visitante_raw == '':
                enfrentamiento.anotacion_local = None
                enfrentamiento.anotacion_visitante = None
                enfrentamiento.ganador = None
            elif anotacion_local_raw == '' or anotacion_visitante_raw == '':
                return HttpResponse( _("Debes introducir los dos resultados o dejarlos ambos en blanco."), status=400 )
            else:
                try:
                    anotacion_local    = int(anotacion_local_raw)
                    anotacion_visitante = int(anotacion_visitante_raw)
                except (ValueError, TypeError):
                    return HttpResponse(_("Los valores de anotación introducidos no son válidos."), status=400)

                if anotacion_local < 0 or anotacion_visitante < 0:
                    return HttpResponse(_("La anotación no puede ser negativa."), status=400)

                if anotacion_local > MAX_SCORE or anotacion_visitante > MAX_SCORE:
                    return HttpResponse(_("La anotación no puede superar 9999."), status=400)

                enfrentamiento.anotacion_local    = anotacion_local
                enfrentamiento.anotacion_visitante = anotacion_visitante

                if enfrentamiento.anotacion_local > enfrentamiento.anotacion_visitante:
                    enfrentamiento.ganador = enfrentamiento.equipo_local
                elif enfrentamiento.anotacion_visitante > enfrentamiento.anotacion_local:
                    enfrentamiento.ganador = enfrentamiento.equipo_visitante
                else:
                    if torneo.deporte == Deporte.BALONCESTO:
                        return HttpResponse( _("En baloncesto no puede haber empates."), status=400 )
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
                
                equipos_torneo = TorneoEquipo.objects.filter(torneo=torneo)
                clas_equipos = Clasificacion.objects.filter(torneo_equipo__in=equipos_torneo)

                if len(equipos_torneo) % 2 == 0:
                    jornadas_necesarias = len(equipos_torneo) - 1
                else:
                    jornadas_necesarias = len(equipos_torneo)
                
                if jornadas_necesarias == max_jornada:
                    ida_vuelta = False
                elif jornadas_necesarias * 2 == max_jornada:
                    ida_vuelta = True
                    

                liga_terminada = True
                n_equipos = len(equipos_torneo)

                for equipo in clas_equipos:
                    partidos_jugados = equipo.victorias + equipo.empates + equipo.derrotas
                    if ida_vuelta:
                        if partidos_jugados < 2 * (n_equipos - 1):
                            liga_terminada = False
                            break
                    else:
                        if partidos_jugados < n_equipos - 1:
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
                else:
                    actualizar_eliminatoria(enfrentamiento)


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
                equipos_torneo = TorneoEquipo.objects.filter(torneo=torneo)
                clas_equipos = Clasificacion.objects.filter(torneo_equipo__in=equipos_torneo)

                grupos = {}
                for eq in clas_equipos:
                    grupos.setdefault(eq.grupo, []).append(eq)
                
                maximo_grupo = max(len(eq) for eq in grupos.values())

                if maximo_grupo % 2 == 0:
                    jornadas_necesarias = maximo_grupo - 1
                else:
                    jornadas_necesarias = maximo_grupo

                if jornadas_necesarias == max_jornada:
                    ida_vuelta = False
                elif jornadas_necesarias * 2 == max_jornada:
                    ida_vuelta = True

                fase_grupos_terminada = True

                for grupo, equipos in grupos.items():
                    n_eq = len(equipos)
                    if ida_vuelta:
                        max_partidos = 2 * (n_eq - 1)
                    else:
                        max_partidos = n_eq - 1

                    for eq in equipos:
                        partidos_jugados = eq.victorias + eq.empates + eq.derrotas
                        if partidos_jugados < max_partidos:
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

        actualizar_estadisticas_generales(torneo, enfrentamiento)

        return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=n_ronda)
                    
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    




@login_required
def generar_enfrentamientos_personalizados(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    equipos = TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo')
    niveles = Nivel.choices
    usuario = request.user

    if not tiene_permiso(usuario, torneo):
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    
    if request.method == 'POST':
        niveles = {}
        iguales = True
        for equipo in equipos:
            valor = request.POST.get(f"nivel-{equipo.equipo.id}")
            if valor:
                nivel = int(valor)
                if equipo.nivel != nivel:
                    iguales = False
                equipo.nivel = nivel
                equipo.save()
                niveles[equipo.equipo.id] = int(nivel)

        ida_vuelta = False
        if (torneo.tipo == TipoTorneo.LIGA or torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS) and request.POST.get("ida-vuelta") == "on":
            ida_vuelta = True

        limpiar_datos_torneo(torneo)

        if torneo.tipo == TipoTorneo.LIGA:
            if iguales:
                generar_liga_aleatorio(torneo, ida_vuelta)
            else:
                generar_liga_personalizado(torneo, niveles, ida_vuelta)

        elif torneo.tipo == TipoTorneo.ELIMINATORIA:
            if iguales:
                generar_eliminatoria_aleatorio(torneo)
            else:
                generar_eliminatoria_personalizado(torneo, niveles)

        elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            if iguales:
                generar_fase_grupos_aleatorio(torneo, ida_vuelta)
            else:
                generar_fase_grupos_personalizado(torneo, niveles, ida_vuelta)

        return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=1)
        

    return render(request, 'enfrentamientos/enfrentamientos_personalizados.html', {'torneo': torneo, 'equipos': equipos, 'niveles': niveles})



@login_required
@require_POST
def generar_enfrentamientos_aleatorios(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user

    if not tiene_permiso(usuario, torneo):
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

    limpiar_datos_torneo(torneo)

    if torneo.tipo == TipoTorneo.LIGA:
        generar_liga_aleatorio(torneo)
    elif torneo.tipo == TipoTorneo.ELIMINATORIA:
        generar_eliminatoria_aleatorio(torneo)
    elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        generar_fase_grupos_aleatorio(torneo)

    return redirect('enfrentamientos:enfrentamientos_torneo', torneo_id=torneo.id, n_ronda=1)
    
    



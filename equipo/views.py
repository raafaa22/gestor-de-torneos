from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Q

from .models import Equipo
from usuario.models import Jugador
from usuario.forms import JugadorForm, UserUpdateForm, UserRegisterForm
from enfrentamiento.models import Enfrentamiento
from torneo.models import Torneo, TorneoEquipo, Clasificacion, Eliminatoria
from gestor.choices import TipoTorneo, TipoUsuario, Deporte
from torneo.views import tipo_usuario
from enfrentamiento.libs import RONDAS, baja_equipo_torneo, alta_equipo_torneo
from estadisticas.models import EstadisticasFutbol, EstadisticasBaloncesto


def torneo_empezado(torneo):
    """Devuelve True si el torneo tiene al menos un enfrentamiento ya jugado."""
    if torneo.deporte == Deporte.PADEL:
        jugado_q = Q(ganador__isnull=False)
    else:
        jugado_q = Q(anotacion_local__isnull=False, anotacion_visitante__isnull=False)

    if torneo.tipo == TipoTorneo.LIGA or torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        return Enfrentamiento.objects.filter(jornada__torneo=torneo).filter(jugado_q).exists()
    elif torneo.tipo == TipoTorneo.ELIMINATORIA:
        return Enfrentamiento.objects.filter(eliminatoria__torneo=torneo).filter(jugado_q).exists()
    return False


def torneo_lleno(torneo):
    """Devuelve True si el torneo ha alcanzado su cupo máximo de equipos."""
    return TorneoEquipo.objects.filter(torneo=torneo).count() >= torneo.max_equipos


@login_required
def dashboard(request):
    usuario = request.user
    equipo = Equipo.objects.filter(user=usuario).first()
    tipo = tipo_usuario(usuario)

    if equipo is None:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))
    
    datos = []

    torneo_equipo = TorneoEquipo.objects.filter(equipo=equipo)
    for te in torneo_equipo:
        id = te.torneo.id
        nombre = te.torneo.nombre
        tipo = te.torneo.tipo
        if tipo == TipoTorneo.LIGA or tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            clasificacion = Clasificacion.objects.filter(torneo_equipo=te).first()
            pos = None
            favor = None
            contra = None
            if clasificacion is None:
                pos = "N/D"
                favor = "N/D"
                contra = "N/D"
            else:
                pos = "%(n)sº" % {'n': clasificacion.posicion}
                favor = clasificacion.anotacion_favor
                contra = clasificacion.anotacion_contra
            datos.append({
                'id': id,
                'nombre': nombre,
                'tipo': TipoTorneo(tipo).label,
                'estado': pos,
                'anotacion_favor': favor,
                'anotacion_contra': contra
            })

        elif tipo == TipoTorneo.ELIMINATORIA:
            eliminatoria = Eliminatoria.objects.filter(torneo=te.torneo).first()
            ronda_actual = "N/D"
            anotacion_favor = "N/D"
            anotacion_contra = "N/D"
            if eliminatoria is not None:
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
                            continue

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

    if equipo is None:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))

    torneo = get_object_or_404(Torneo, id=torneo_id)
    if not TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).exists():
        return HttpResponseForbidden(_("No estás inscrito en este torneo."))

    baja_equipo_torneo(torneo, equipo)

    return redirect('equipo:dashboard')

@login_required
def listado_torneos_inscribir(request, equipo_id):
    usuario = request.user
    equipo = get_object_or_404(Equipo, id=equipo_id)
    tipo = tipo_usuario(usuario)

    if tipo != TipoUsuario.EQUIPO and tipo != TipoUsuario.ADMINISTRADOR:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))
    
    if tipo == TipoUsuario.EQUIPO and equipo.user != usuario:
        return HttpResponseForbidden(_("Esta página no es de tu equipo"))
    
    torneos_disp = Torneo.objects.filter(deporte=equipo.deporte).exclude(torneo_equipos__equipo=equipo)
    torneos = []
    for torneo in torneos_disp:
        if torneo_empezado(torneo):
            continue
        if torneo_lleno(torneo):
            continue
        torneos.append(torneo)

    return render(request, 'equipo/listado_torneos.html', {'torneos': torneos, 'equipo': equipo})

@login_required
def listado_jugadores(request, equipo_id):
    usuario = request.user
    equipo = get_object_or_404(Equipo, id=equipo_id)
    tipo = tipo_usuario(usuario)

    if tipo != TipoUsuario.EQUIPO and tipo != TipoUsuario.ADMINISTRADOR:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))
    
    if tipo == TipoUsuario.EQUIPO and equipo.user != usuario:
        return HttpResponseForbidden(_("Estos no son tus jugadores."))
    
    if equipo.deporte == Deporte.PADEL:
        return HttpResponseForbidden(_("En pádel los propios jugadores son el equipo, por lo que tu equipo no tiene jugadores."))
    
    jugadores = Jugador.objects.filter(equipo=equipo)

    return render(request, 'equipo/listado_jugadores.html', {'jugadores': jugadores, 'equipo': equipo})


@login_required
@transaction.atomic
def crear_jugador(request, equipo_id):
    usuario = request.user
    equipo = get_object_or_404(Equipo, id=equipo_id)
    tipo = tipo_usuario(usuario)

    if tipo != TipoUsuario.EQUIPO and tipo != TipoUsuario.ADMINISTRADOR:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))

    if tipo == TipoUsuario.EQUIPO and equipo.user != usuario:
        return HttpResponseForbidden(_("No puedes crear jugadores en otros equipos."))

    if equipo.deporte == Deporte.PADEL:
        return HttpResponseForbidden(_("En pádel los propios jugadores son el equipo, por lo que tu equipo no tiene jugadores."))

    if request.method == 'POST':
        user_form = UserRegisterForm(request.POST)
        jugador_form = JugadorForm(request.POST, equipo=equipo)
        
        # Verificar si se debe usar contraseña por defecto
        usar_password_defecto = request.POST.get('usar_password_defecto') == 'true'
        
        # Debug: imprimir el valor recibido
        print(f"DEBUG: usar_password_defecto field = {request.POST.get('usar_password_defecto')}")
        print(f"DEBUG: usar_password_defecto bool = {usar_password_defecto}")

        if user_form.is_valid() and jugador_form.is_valid():
            user = user_form.save()

            es_portero_nuevo = equipo.deporte == Deporte.FUTBOL and jugador_form.cleaned_data.get("es_portero")

            antiguo_portero = None
            if es_portero_nuevo:
                antiguo_portero = Jugador.objects.filter(equipo=equipo, es_portero=True).first()
                Jugador.objects.filter(equipo=equipo, es_portero=True).update(es_portero=False)

            jugador = jugador_form.save(commit=False)
            jugador.user = user
            jugador.equipo = equipo
            jugador.tiene_password_por_defecto = usar_password_defecto
            print(f"DEBUG: Setting jugador.tiene_password_por_defecto = {usar_password_defecto}")
            jugador.save()

            for te in TorneoEquipo.objects.filter(equipo=equipo):
                goles_contra = 0 if jugador.es_portero else None
                if te.torneo.deporte == Deporte.FUTBOL:
                    EstadisticasFutbol.objects.create(jugador=jugador, torneo=te.torneo, goles=0, asistencias=0, goles_contra=goles_contra)
                elif te.torneo.deporte == Deporte.BALONCESTO:
                    EstadisticasBaloncesto.objects.create(jugador=jugador, torneo=te.torneo, puntos=0, rebotes=0, asistencias=0)

            if es_portero_nuevo and antiguo_portero:
                for est in EstadisticasFutbol.objects.filter(jugador=antiguo_portero):
                    EstadisticasFutbol.objects.filter(jugador=jugador, torneo=est.torneo).update(goles_contra=est.goles_contra)
                EstadisticasFutbol.objects.filter(jugador=antiguo_portero).update(goles_contra=None)

            return redirect('equipo:listado_jugadores', equipo_id=equipo.id)
    else:
        user_form = UserRegisterForm()
        jugador_form = JugadorForm(equipo=equipo)

    return render(request, 'equipo/nuevo_jugador.html', {'user_form': user_form, 'jugador_form': jugador_form, 'equipo': equipo})


@login_required
@transaction.atomic
def editar_jugador(request, equipo_id, jugador_id):
    usuario = request.user
    equipo = get_object_or_404(Equipo, id=equipo_id)
    tipo = tipo_usuario(usuario)

    if tipo != TipoUsuario.EQUIPO and tipo != TipoUsuario.ADMINISTRADOR:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))
    
    if tipo == TipoUsuario.EQUIPO and equipo.user != usuario:
        return HttpResponseForbidden(_("No puedes modificar jugadores de otros equipos."))
    
    if equipo.deporte == Deporte.PADEL:
        return HttpResponseForbidden(_("En pádel los propios jugadores son el equipo, por lo que tu equipo no tiene jugadores."))
    
    jugador = get_object_or_404(Jugador, dni=jugador_id, equipo=equipo)

    if request.method == 'POST':
        era_portero = jugador.es_portero
        user_form = UserUpdateForm(request.POST, instance=jugador.user)
        jugador_form = JugadorForm(request.POST, instance=jugador, equipo=equipo, is_admin=False)

        if user_form.is_valid() and jugador_form.is_valid():
            user_form.save()

            if equipo.deporte == Deporte.FUTBOL and jugador_form.cleaned_data.get("es_portero"):
                if not era_portero:
                    antiguo_portero = Jugador.objects.filter(equipo=equipo, es_portero=True).first()
                    if antiguo_portero:
                        for est in EstadisticasFutbol.objects.filter(jugador=antiguo_portero):
                            EstadisticasFutbol.objects.filter(jugador=jugador, torneo=est.torneo).update(goles_contra=est.goles_contra)
                        EstadisticasFutbol.objects.filter(jugador=antiguo_portero).update(goles_contra=None)
                    else:
                        EstadisticasFutbol.objects.filter(jugador=jugador).update(goles_contra=0)
                Jugador.objects.filter(equipo=equipo, es_portero=True).exclude(dni=jugador.dni).update(es_portero=False)

            elif equipo.deporte == Deporte.FUTBOL and era_portero and not jugador_form.cleaned_data.get("es_portero"):
                EstadisticasFutbol.objects.filter(jugador=jugador).update(goles_contra=None)
            
            jugador_form.save()

            return redirect('equipo:listado_jugadores', equipo_id=equipo.id)
    else:
        user_form = UserUpdateForm(instance=jugador.user)
        jugador_form = JugadorForm(instance=jugador, equipo=equipo, is_admin=False)
    

    return render(request, 'equipo/editar_jugador.html', {'user_form': user_form, 'jugador_form': jugador_form, 'equipo': equipo, 'jugador': jugador})


@login_required
@require_POST
def borrar_jugador(request, equipo_id, jugador_id):
    usuario = request.user
    equipo = get_object_or_404(Equipo, id=equipo_id)
    tipo = tipo_usuario(usuario)

    if tipo != TipoUsuario.EQUIPO and tipo != TipoUsuario.ADMINISTRADOR:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))
    
    if tipo == TipoUsuario.EQUIPO and equipo.user != usuario:
        return HttpResponseForbidden(_("No puedes borrar jugadores de otros equipos."))
    
    if equipo.deporte == Deporte.PADEL:
        return HttpResponseForbidden(_("En pádel los propios jugadores son el equipo, por lo que tu equipo no tiene jugadores."))
    
    jugador = get_object_or_404(Jugador, dni=jugador_id, equipo=equipo)

    jugador.user.delete()

    return redirect('equipo:listado_jugadores', equipo_id=equipo.id)



@login_required
@require_POST
@transaction.atomic
def inscribir_equipo_torneo(request, torneo_id, equipo_id):
    usuario = request.user
    equipo = get_object_or_404(Equipo, id=equipo_id)
    tipo = tipo_usuario(usuario)

    if tipo != TipoUsuario.EQUIPO and tipo != TipoUsuario.ADMINISTRADOR:
        return HttpResponseForbidden(_("No tienes permiso para acceder a esta página."))

    
    if tipo == TipoUsuario.EQUIPO and equipo.user != usuario:
        return HttpResponseForbidden(_("No puedes inscribir otros equipos en torneos."))

    torneo = get_object_or_404(Torneo, id=torneo_id)

    if torneo_empezado(torneo):
        return HttpResponseForbidden(_("No puedes inscribirte en un torneo que ya ha empezado."))

    if torneo_lleno(torneo):
        return HttpResponseForbidden(_("El torneo ya ha alcanzado el número máximo de equipos."))

    alta_equipo_torneo(torneo, equipo)

    return redirect('equipo:dashboard')

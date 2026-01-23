from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseForbidden, JsonResponse

from usuario.models import Organizador, Administrador, Jugador
from equipo.models import Equipo
from .models import Torneo, TorneoEquipo, Clasificacion
from .forms import CrearTorneoForm
from gestor.choices import TipoTorneo, TipoUsuario


def tipo_usuario(usuario):
    if Administrador.objects.filter(user=usuario).exists():
        return TipoUsuario.ADMINISTRADOR
    elif Organizador.objects.filter(user=usuario).exists():
        return TipoUsuario.ORGANIZADOR
    elif Equipo.objects.filter(user=usuario).exists():
        return TipoUsuario.EQUIPO
    elif Jugador.objects.filter(user=usuario).exists():
        return TipoUsuario.JUGADOR

@login_required
def jugador_dashboard(request):
    return render(request, 'torneo/jugador_dashboard.html')

@login_required
def organizador_dashboard(request):
    usuario = request.user
    tipo = tipo_usuario(usuario)

    if tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR:
        if tipo == TipoUsuario.ADMINISTRADOR:
            return redirect('usuario:admin_dashboard')
        
        organizador = get_object_or_404(Organizador, user=usuario)
        torneos = Torneo.objects.filter(organizador=organizador)
        return render(request, 'torneo/organizador_dashboard.html', {'torneos': torneos})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    

@login_required
@require_POST
def borrar_torneo(request, torneo_id : int):
    usuario = request.user

    tipo = tipo_usuario(usuario)
    if tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR:
        torneo = get_object_or_404(Torneo, id=torneo_id)
        torneo.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"ok": True})
        
        return redirect('torneo:organizador')
    
    else:
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    


@login_required
def crear_torneo(request):
    user = request.user

    tipo = tipo_usuario(user)

    if tipo == TipoUsuario.ADMINISTRADOR or tipo == TipoUsuario.ORGANIZADOR:
        if request.method == 'POST':
            form = CrearTorneoForm(request.POST, user=user)
            if form.is_valid():
                form.save()
                if tipo == TipoUsuario.ADMINISTRADOR:
                    return redirect('usuario:admin_dashboard')
                else:
                    return redirect('torneo:organizador')
        else:
            form = CrearTorneoForm(user=user)
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

    return render(request, 'torneo/nuevo_torneo.html', {'form': form})




def tiene_permiso(usuario, torneo: Torneo):
    tipo = tipo_usuario(usuario)

    if tipo == TipoUsuario.ADMINISTRADOR:
        return True
    
    if tipo == TipoUsuario.ORGANIZADOR and torneo.organizador.user == usuario:
        return True
    
    if tipo == TipoUsuario.EQUIPO:
        equipo = Equipo.objects.filter(user=usuario).first()
        if TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).exists():
            return True
        
    if tipo == TipoUsuario.JUGADOR:
        jugador = Jugador.objects.filter(user=usuario).first()
        if TorneoEquipo.objects.filter(torneo=torneo, equipo=jugador.equipo).exists():
            return True
        
    return False



@login_required
def principal_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user


    if tiene_permiso(usuario, torneo):
        if torneo.tipo == TipoTorneo.LIGA or torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            return redirect('torneo:clasificacion_torneo', torneo_id=torneo.id)
    
        if torneo.tipo == TipoTorneo.ELIMINATORIA:
            return redirect('torneo:enfrentamientos_torneo', torneo_id=torneo.id)
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    


@login_required
def clasificacion_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user

    if tiene_permiso(usuario, torneo):
        clasificacion = Clasificacion.objects.filter(torneo=torneo).order_by('posicion')
        return render(request, 'torneo/clasificacion.html', {'torneo': torneo, 'clasificacion': clasificacion})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

@login_required
def enfrentamientos_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    return render(request, 'torneo/enfrentamientos.html', {'torneo': torneo})

@login_required
def estadisticas_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    return render(request, 'torneo/estadisticas_torneo.html', {'torneo': torneo})

@login_required
def informacion_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user
    tipo = tipo_usuario(usuario)

    if tiene_permiso(usuario, torneo):
        if tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR:
            if request.method == 'POST':
                form = CrearTorneoForm(request.POST, instance=torneo, user=usuario)
                if form.is_valid():
                    form.save()
                    return redirect('torneo:principal_torneo', torneo_id=torneo.id)
            else:
                form = CrearTorneoForm(instance=torneo, user=usuario)

            return render(request, 'torneo/info_torneo.html', {'torneo': torneo, 'form': form, 'editor': True})
        else:
            return render(request, 'torneo/info_torneo.html', {'torneo': torneo, 'editor': False})
        
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    

@login_required
def equipos_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user

    if tiene_permiso(usuario, torneo):
        equipos_torneo = TorneoEquipo.objects.filter(torneo=torneo)
        equipos = [te.equipo for te in equipos_torneo]
        return render(request, 'torneo/equipos_torneo.html', {'torneo': torneo, 'equipos': equipos})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )
    

@login_required
@require_POST
def borrar_equipo_torneo(request, torneo_id: int, equipo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user

    tipo = tipo_usuario(usuario)

    if tipo == TipoUsuario.ORGANIZADOR or tipo == TipoUsuario.ADMINISTRADOR:
        equipo = get_object_or_404(Equipo, id=equipo_id)
        torneo_equipo = TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).first()
        if torneo_equipo:
            torneo_equipo.delete()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"ok": True})
            
            return redirect('torneo:equipos_torneo', torneo_id=torneo.id)
        else:
            return JsonResponse({"ok": False, "error": "El equipo no está en el torneo"}, status=404)
    else:
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)

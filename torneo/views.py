from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseForbidden, JsonResponse
from usuario.models import Organizador, Administrador
from .models import Torneo
from gestor.choices import TipoTorneo

@login_required
def jugador_dashboard(request):
    return render(request, 'torneo/jugador_dashboard.html')

@login_required
def organizador_dashboard(request):
    usuario = request.user

    is_organizador = Organizador.objects.filter(user=usuario).exists()
    is_admin = Administrador.objects.filter(user=usuario).exists()

    if is_organizador or is_admin:
        if is_admin:
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

    is_organizador = Organizador.objects.filter(user=usuario).exists()
    is_admin = Administrador.objects.filter(user=usuario).exists()

    if is_organizador or is_admin:
        torneo = get_object_or_404(Torneo, id=torneo_id)
        torneo.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"ok": True})
        
        return redirect('torneo:organizador')
    
    else:
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    


@login_required
def crear_torneo(request):
    return render(request, 'torneo/nuevo_torneo.html')


@login_required
def principal_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    if torneo.tipo == TipoTorneo.LIGA or torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        return render(request, 'torneo/clasificacion.html', {'torneo': torneo})
    
    if torneo.tipo == TipoTorneo.ELIMINATORIA:
        return render(request, 'torneo/enfrentamientos.html', {'torneo': torneo})


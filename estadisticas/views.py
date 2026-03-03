from django.shortcuts import render
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden

from .models import EstadisticasBaloncesto, EstadisticasFutbol
from torneo.models import Torneo
from torneo.views import tiene_permiso



@login_required
def estadisticas_torneo(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    usuario = request.user

    if tiene_permiso(usuario, torneo):
        if torneo.deporte == 'FUT':
            goles = EstadisticasFutbol.objects.filter(torneo=torneo).order_by('goles')
            asistencias = EstadisticasFutbol.objects.filter(torneo=torneo).order_by('asistencias')
            goles_contra = EstadisticasFutbol.objects.filter(torneo=torneo, goles_contra__isnull=False).order_by('goles_contra')
            estadisticas = {
                'goles': goles,
                'asistencias': asistencias,
                'goles_contra': goles_contra
            }
        else:
            puntos = EstadisticasBaloncesto.objects.filter(torneo=torneo).order_by('puntos')
            rebotes = EstadisticasBaloncesto.objects.filter(torneo=torneo).order_by('rebotes')
            asistencias = EstadisticasBaloncesto.objects.filter(torneo=torneo).order_by('asistencias')
            estadisticas = {
                'puntos': puntos,
                'rebotes': rebotes,
                'asistencias': asistencias
            }
        return render(request, 'torneo/estadisticas_torneo.html', {'torneo': torneo, 'estadisticas': estadisticas})
    else:
        return HttpResponseForbidden( _("No tienes permiso para acceder a esta página.") )

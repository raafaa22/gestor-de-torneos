from random import shuffle
from math import log2
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.db import transaction
from django.db.models import Q, Sum, F, ExpressionWrapper, IntegerField


from gestor.choices import Deporte, TipoTorneo, EstadisticaBaloncesto, EstadisticaFutbol, TipoRonda
from torneo.models import Torneo, Eliminatoria, EliminatoriaGrupos, Clasificacion, TorneoEquipo, Jornada
from estadisticas.models import EstadisticasFutbol, EstadisticasBaloncesto
from equipo.models import Equipo
from .models import Enfrentamiento, GuardadoEnfrentamiento, EstadisticasEnfrentamiento
from usuario.models import Jugador


RONDAS = [
    TipoRonda.DIECISEISAVOS,
    TipoRonda.OCTAVOS,
    TipoRonda.CUARTOS,
    TipoRonda.SEMIFINAL,
    TipoRonda.FINAL
]


@transaction.atomic
def alta_equipo_torneo(torneo: Torneo, equipo: Equipo) -> bool:
    """Inscribe un equipo en un torneo y crea la clasificación + estadísticas necesarias.

    Devuelve True si se inscribió, False si ya estaba inscrito.
    El caller es responsable de validar permisos y los checks
    de torneo_empezado / torneo_lleno antes de invocar esta función.
    """
    torneo_equipo, created = TorneoEquipo.objects.get_or_create(torneo=torneo, equipo=equipo)
    if not created:
        return False

    if torneo.tipo == TipoTorneo.LIGA:
        posicion_max = Clasificacion.objects.filter(
            torneo_equipo__torneo=torneo
        ).order_by('-posicion').values_list('posicion', flat=True).first()
        if posicion_max is None:
            posicion_max = 0

        Clasificacion.objects.create(
            torneo_equipo=torneo_equipo,
            grupo="GENERAL",
            posicion=posicion_max + 1,
            puntos=0,
            victorias=0,
            empates=0,
            derrotas=0,
            anotacion_favor=0,
            anotacion_contra=0,
        )

    if torneo.deporte != Deporte.PADEL:
        jugadores = Jugador.objects.filter(equipo=equipo)
        for jugador in jugadores:
            if torneo.deporte == Deporte.FUTBOL:
                goles_contra = 0 if jugador.es_portero else None
                EstadisticasFutbol.objects.create(
                    jugador=jugador, torneo=torneo,
                    goles=0, asistencias=0, goles_contra=goles_contra,
                )
            elif torneo.deporte == Deporte.BALONCESTO:
                EstadisticasBaloncesto.objects.create(
                    jugador=jugador, torneo=torneo,
                    puntos=0, rebotes=0, asistencias=0,
                )

    return True


@transaction.atomic
def baja_equipo_torneo(torneo: Torneo, equipo: Equipo):
    torneo_equipo = TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).first()
    if not torneo_equipo:
        return

    jugadores = Jugador.objects.filter(equipo=equipo)
    equipos_afectados = set()

    grupo_equipo = None
    if torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        clasif = Clasificacion.objects.filter(torneo_equipo=torneo_equipo).first()
        if clasif:
            grupo_equipo = clasif.grupo

    if torneo.tipo in (TipoTorneo.LIGA, TipoTorneo.ELIMINATORIA_GRUPOS):
        enfrentamientos_jornada = Enfrentamiento.objects.filter(
            jornada__torneo=torneo
        ).filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo))

        for enf in enfrentamientos_jornada:
            if enf.equipo_local == equipo and enf.equipo_visitante:
                equipos_afectados.add(enf.equipo_visitante)
            elif enf.equipo_visitante == equipo and enf.equipo_local:
                equipos_afectados.add(enf.equipo_local)

        enfrentamientos_jornada.delete()

    if torneo.tipo in (TipoTorneo.ELIMINATORIA, TipoTorneo.ELIMINATORIA_GRUPOS, TipoTorneo.LIGA):
        eliminatoria = Eliminatoria.objects.filter(torneo=torneo).first()
        if eliminatoria:
            # Antes de propagar al siguiente, limpiar cualquier ganador/anotacion
            # que apunte al equipo que se va: al cambiar equipo_local/equipo_visitante
            # de los enfrentamientos siguientes se violaría
            # enfrentamiento_ganador_local_o_visitante si quedase un ganador huérfano.
            Enfrentamiento.objects.filter(eliminatoria=eliminatoria, ganador=equipo).update(
                ganador=None,
                anotacion_local=None,
                anotacion_visitante=None,
                juegos_local_1=None,
                juegos_visitante_1=None,
                juegos_local_2=None,
                juegos_visitante_2=None,
                juegos_local_3=None,
                juegos_visitante_3=None,
            )

            enfrentamientos_elim = list(Enfrentamiento.objects.filter(
                eliminatoria=eliminatoria
            ).filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo)))

            for enf in enfrentamientos_elim:
                oponente = enf.equipo_visitante if enf.equipo_local == equipo else enf.equipo_local

                if oponente:
                    sig = Enfrentamiento.objects.filter(eliminatoria=eliminatoria, prev_local=enf).first()
                    if sig:
                        sig.equipo_local = oponente
                        sig.prev_local = None
                        sig.save()
                    else:
                        sig = Enfrentamiento.objects.filter(eliminatoria=eliminatoria, prev_visitante=enf).first()
                        if sig:
                            sig.equipo_visitante = oponente
                            sig.prev_visitante = None
                            sig.save()

                enf.delete()


    if torneo.deporte == Deporte.FUTBOL:
        EstadisticasFutbol.objects.filter(torneo=torneo, jugador__in=jugadores).delete()
    elif torneo.deporte == Deporte.BALONCESTO:
        EstadisticasBaloncesto.objects.filter(torneo=torneo, jugador__in=jugadores).delete()

    torneo_equipo.delete()

    if torneo.tipo in (TipoTorneo.LIGA, TipoTorneo.ELIMINATORIA_GRUPOS):
        for eq in equipos_afectados:
            recalcular_clasificacion_equipo(torneo, eq)

        if torneo.tipo == TipoTorneo.LIGA:
            clasificaciones = Clasificacion.objects.filter(
                torneo_equipo__torneo=torneo
            ).annotate(
                dif=ExpressionWrapper(F('anotacion_favor') - F('anotacion_contra'), output_field=IntegerField())
            ).order_by('-puntos', '-victorias', '-dif', 'derrotas', '-anotacion_favor', 'anotacion_contra')

            for i, c in enumerate(clasificaciones):
                c.posicion = i + 1
                c.save()

        elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS and grupo_equipo:
            clasificaciones = Clasificacion.objects.filter(
                torneo_equipo__torneo=torneo, grupo=grupo_equipo
            ).annotate(
                dif=ExpressionWrapper(F('anotacion_favor') - F('anotacion_contra'), output_field=IntegerField())
            ).order_by('-puntos', '-victorias', '-dif', 'derrotas', '-anotacion_favor', 'anotacion_contra')

            for i, c in enumerate(clasificaciones):
                c.posicion = i + 1
                c.save()


@transaction.atomic
def limpiar_datos_torneo(torneo: Torneo):
    Enfrentamiento.objects.filter(
        Q(jornada__torneo=torneo) | Q(eliminatoria__torneo=torneo)
    ).delete()
    Jornada.objects.filter(torneo=torneo).delete()
    Eliminatoria.objects.filter(torneo=torneo).delete()

    EstadisticasFutbol.objects.filter(torneo=torneo).update(goles=0, asistencias=0)
    EstadisticasFutbol.objects.filter(torneo=torneo, goles_contra__isnull=False).update(goles_contra=0)
    EstadisticasBaloncesto.objects.filter(torneo=torneo).update(puntos=0, rebotes=0, asistencias=0)

    if torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        Clasificacion.objects.filter(torneo_equipo__torneo=torneo).delete()
    else:
        Clasificacion.objects.filter(torneo_equipo__torneo=torneo).update(
            puntos=0, victorias=0, empates=0, derrotas=0,
            anotacion_favor=0, anotacion_contra=0
        )

    torneo.ganador = None
    torneo.save()

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

    
    #Recalcular todos los datos de la clasificacion de estos equipos
    
    qs_local = Enfrentamiento.objects.filter(
        Q(equipo_local=enfrentamiento.equipo_local) | Q(equipo_visitante=enfrentamiento.equipo_local),
        jornada__torneo=torneo
    )

    qs_visitante = Enfrentamiento.objects.filter(
        Q(equipo_local=enfrentamiento.equipo_visitante) | Q(equipo_visitante=enfrentamiento.equipo_visitante),
        jornada__torneo=torneo
    )

    if torneo.deporte == Deporte.PADEL:
        qs_local_jugados = qs_local.filter(ganador__isnull=False)
        qs_visitante_jugados = qs_visitante.filter(ganador__isnull=False)

        anotacion_local = qs_local_jugados.aggregate(
            juegos_local_1=Sum('juegos_local_1', filter=Q(equipo_local=enfrentamiento.equipo_local)),
            juegos_local_2=Sum('juegos_local_2', filter=Q(equipo_local=enfrentamiento.equipo_local)),
            juegos_local_3=Sum('juegos_local_3', filter=Q(equipo_local=enfrentamiento.equipo_local)),

            juegos_visitante_1=Sum('juegos_visitante_1', filter=Q(equipo_visitante=enfrentamiento.equipo_local)),
            juegos_visitante_2=Sum('juegos_visitante_2', filter=Q(equipo_visitante=enfrentamiento.equipo_local)),
            juegos_visitante_3=Sum('juegos_visitante_3', filter=Q(equipo_visitante=enfrentamiento.equipo_local)),

            contra_local_1=Sum('juegos_visitante_1', filter=Q(equipo_local=enfrentamiento.equipo_local)),
            contra_local_2=Sum('juegos_visitante_2', filter=Q(equipo_local=enfrentamiento.equipo_local)),
            contra_local_3=Sum('juegos_visitante_3', filter=Q(equipo_local=enfrentamiento.equipo_local)),

            contra_visitante_1=Sum('juegos_local_1', filter=Q(equipo_visitante=enfrentamiento.equipo_local)),
            contra_visitante_2=Sum('juegos_local_2', filter=Q(equipo_visitante=enfrentamiento.equipo_local)),
            contra_visitante_3=Sum('juegos_local_3', filter=Q(equipo_visitante=enfrentamiento.equipo_local))
        )

        anotacion_total_local = (anotacion_local['juegos_local_1'] or 0) + (anotacion_local['juegos_local_2'] or 0) + (anotacion_local['juegos_local_3'] or 0) + (anotacion_local['juegos_visitante_1'] or 0) + (anotacion_local['juegos_visitante_2'] or 0) + (anotacion_local['juegos_visitante_3'] or 0)

        anotacion_contra_local = (anotacion_local['contra_local_1'] or 0) + (anotacion_local['contra_local_2'] or 0) + (anotacion_local['contra_local_3'] or 0) + (anotacion_local['contra_visitante_1'] or 0) + (anotacion_local['contra_visitante_2'] or 0) + (anotacion_local['contra_visitante_3'] or 0)


        anotacion_visitante = qs_visitante_jugados.aggregate(
            juegos_local_1=Sum('juegos_local_1', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),
            juegos_local_2=Sum('juegos_local_2', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),
            juegos_local_3=Sum('juegos_local_3', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),

            juegos_visitante_1=Sum('juegos_visitante_1', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante)),
            juegos_visitante_2=Sum('juegos_visitante_2', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante)),
            juegos_visitante_3=Sum('juegos_visitante_3', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante)),

            contra_local_1=Sum('juegos_visitante_1', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),
            contra_local_2=Sum('juegos_visitante_2', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),
            contra_local_3=Sum('juegos_visitante_3', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),

            contra_visitante_1=Sum('juegos_local_1', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante)),
            contra_visitante_2=Sum('juegos_local_2', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante)),
            contra_visitante_3=Sum('juegos_local_3', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante))
        )

        anotacion_total_visitante = (anotacion_visitante['juegos_local_1'] or 0) + (anotacion_visitante['juegos_local_2'] or 0) + (anotacion_visitante['juegos_local_3'] or 0) + (anotacion_visitante['juegos_visitante_1'] or 0) + (anotacion_visitante['juegos_visitante_2'] or 0) + (anotacion_visitante['juegos_visitante_3'] or 0)

        anotacion_contra_visitante = (anotacion_visitante['contra_local_1'] or 0) + (anotacion_visitante['contra_local_2'] or 0) + (anotacion_visitante['contra_local_3'] or 0) + (anotacion_visitante['contra_visitante_1'] or 0) + (anotacion_visitante['contra_visitante_2'] or 0) + (anotacion_visitante['contra_visitante_3'] or 0)

    else:
        qs_local_jugados = qs_local.filter(anotacion_local__isnull=False, anotacion_visitante__isnull=False)
        qs_visitante_jugados = qs_visitante.filter(anotacion_local__isnull=False, anotacion_visitante__isnull=False)

        anotacion_local = qs_local_jugados.aggregate(
            total_local=Sum('anotacion_local', filter=Q(equipo_local=enfrentamiento.equipo_local)),
            total_visitante=Sum('anotacion_visitante', filter=Q(equipo_visitante=enfrentamiento.equipo_local)),
            contra_local=Sum('anotacion_visitante', filter=Q(equipo_local=enfrentamiento.equipo_local)),
            contra_visitante=Sum('anotacion_local', filter=Q(equipo_visitante=enfrentamiento.equipo_local))
        )
        anotacion_contra_local = (anotacion_local['contra_local'] or 0) + (anotacion_local['contra_visitante'] or 0)
        anotacion_total_local = (anotacion_local['total_local'] or 0) + (anotacion_local['total_visitante'] or 0)

        anotacion_visitante = qs_visitante_jugados.aggregate(
            total_local=Sum('anotacion_local', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),
            total_visitante=Sum('anotacion_visitante', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante)),
            contra_local=Sum('anotacion_visitante', filter=Q(equipo_local=enfrentamiento.equipo_visitante)),
            contra_visitante=Sum('anotacion_local', filter=Q(equipo_visitante=enfrentamiento.equipo_visitante))
        )
        anotacion_total_visitante = (anotacion_visitante['total_local'] or 0) + (anotacion_visitante['total_visitante'] or 0)
        anotacion_contra_visitante = (anotacion_visitante['contra_local'] or 0) + (anotacion_visitante['contra_visitante'] or 0)

    victorias_local = qs_local_jugados.filter(ganador=enfrentamiento.equipo_local).count()
    derrotas_local = qs_local_jugados.exclude(ganador__isnull=True).exclude(ganador=enfrentamiento.equipo_local).count()

    victorias_visitante = qs_visitante_jugados.filter(ganador=enfrentamiento.equipo_visitante).count()
    derrotas_visitante = qs_visitante_jugados.exclude(ganador__isnull=True).exclude(ganador=enfrentamiento.equipo_visitante).count()

    if torneo.deporte == Deporte.FUTBOL:
        empates_local = qs_local_jugados.filter(ganador__isnull=True).count()
        empates_visitante = qs_visitante_jugados.filter(ganador__isnull=True).count()

        #Actualizamos porteros
        portero_local = Jugador.objects.filter(equipo=enfrentamiento.equipo_local, es_portero=True).first()
        portero_visitante = Jugador.objects.filter(equipo=enfrentamiento.equipo_visitante, es_portero=True).first()

        if portero_local:
            estadisticas_portero_local = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=portero_local).first()
            estadisticas_portero_local.goles_contra = anotacion_contra_local
            estadisticas_portero_local.save()
        
        if portero_visitante:
            estadisticas_portero_visitante = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=portero_visitante).first()
            estadisticas_portero_visitante.goles_contra = anotacion_contra_visitante
            estadisticas_portero_visitante.save()
    else:
        empates_local = 0
        empates_visitante = 0
        


    puntos_local = victorias_local * puntos_ganador + derrotas_local * puntos_perdedor + empates_local

    clasif_local.puntos = puntos_local
    clasif_local.victorias = victorias_local
    clasif_local.empates = empates_local
    clasif_local.derrotas = derrotas_local
    clasif_local.anotacion_favor= anotacion_total_local
    clasif_local.anotacion_contra = anotacion_contra_local

    

    puntos_visitante = victorias_visitante * puntos_ganador + derrotas_visitante * puntos_perdedor + empates_visitante

    clasif_visitante.puntos = puntos_visitante
    clasif_visitante.victorias = victorias_visitante
    clasif_visitante.empates = empates_visitante
    clasif_visitante.derrotas = derrotas_visitante
    clasif_visitante.anotacion_favor = anotacion_total_visitante
    clasif_visitante.anotacion_contra = anotacion_contra_visitante
    

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
        grupo = clasif_local.grupo
        equipos = Clasificacion.objects.filter(torneo_equipo__torneo=torneo, grupo=grupo).annotate(
            dif=ExpressionWrapper(F('anotacion_favor') - F('anotacion_contra'), output_field=IntegerField())
        ).order_by('-puntos', '-victorias', '-dif', 'derrotas', '-anotacion_favor', 'anotacion_contra')

        for i, equipo in enumerate(equipos):
            equipo.posicion = i + 1
            equipo.save()


@transaction.atomic
def recalcular_clasificacion_equipo(torneo: Torneo, equipo: Equipo):
    te = TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).first()
    if not te:
        return

    clasif = Clasificacion.objects.filter(torneo_equipo=te).first()
    if not clasif:
        return

    puntos_ganador = 0
    puntos_perdedor = 0

    if torneo.deporte == Deporte.FUTBOL:
        puntos_ganador = 3
    elif torneo.deporte == Deporte.BALONCESTO:
        puntos_ganador = 2
        puntos_perdedor = 1
    else:
        puntos_ganador = 1

    qs = Enfrentamiento.objects.filter(
        Q(equipo_local=equipo) | Q(equipo_visitante=equipo),
        jornada__torneo=torneo
    )

    if torneo.deporte == Deporte.PADEL:
        qs_jugados = qs.filter(ganador__isnull=False)

        datos = qs_jugados.aggregate(
            juegos_local_1=Sum('juegos_local_1', filter=Q(equipo_local=equipo)),
            juegos_local_2=Sum('juegos_local_2', filter=Q(equipo_local=equipo)),
            juegos_local_3=Sum('juegos_local_3', filter=Q(equipo_local=equipo)),
            juegos_visitante_1=Sum('juegos_visitante_1', filter=Q(equipo_visitante=equipo)),
            juegos_visitante_2=Sum('juegos_visitante_2', filter=Q(equipo_visitante=equipo)),
            juegos_visitante_3=Sum('juegos_visitante_3', filter=Q(equipo_visitante=equipo)),
            contra_local_1=Sum('juegos_visitante_1', filter=Q(equipo_local=equipo)),
            contra_local_2=Sum('juegos_visitante_2', filter=Q(equipo_local=equipo)),
            contra_local_3=Sum('juegos_visitante_3', filter=Q(equipo_local=equipo)),
            contra_visitante_1=Sum('juegos_local_1', filter=Q(equipo_visitante=equipo)),
            contra_visitante_2=Sum('juegos_local_2', filter=Q(equipo_visitante=equipo)),
            contra_visitante_3=Sum('juegos_local_3', filter=Q(equipo_visitante=equipo))
        )

        anotacion_favor = sum(datos[k] or 0 for k in [
            'juegos_local_1', 'juegos_local_2', 'juegos_local_3',
            'juegos_visitante_1', 'juegos_visitante_2', 'juegos_visitante_3'
        ])
        anotacion_contra = sum(datos[k] or 0 for k in [
            'contra_local_1', 'contra_local_2', 'contra_local_3',
            'contra_visitante_1', 'contra_visitante_2', 'contra_visitante_3'
        ])
    else:
        qs_jugados = qs.filter(anotacion_local__isnull=False, anotacion_visitante__isnull=False)

        datos = qs_jugados.aggregate(
            total_local=Sum('anotacion_local', filter=Q(equipo_local=equipo)),
            total_visitante=Sum('anotacion_visitante', filter=Q(equipo_visitante=equipo)),
            contra_local=Sum('anotacion_visitante', filter=Q(equipo_local=equipo)),
            contra_visitante=Sum('anotacion_local', filter=Q(equipo_visitante=equipo))
        )
        anotacion_favor = (datos['total_local'] or 0) + (datos['total_visitante'] or 0)
        anotacion_contra = (datos['contra_local'] or 0) + (datos['contra_visitante'] or 0)

    victorias = qs_jugados.filter(ganador=equipo).count()
    derrotas = qs_jugados.exclude(ganador__isnull=True).exclude(ganador=equipo).count()

    if torneo.deporte == Deporte.FUTBOL:
        empates = qs_jugados.filter(ganador__isnull=True).count()
        portero = Jugador.objects.filter(equipo=equipo, es_portero=True).first()
        if portero:
            est = EstadisticasFutbol.objects.filter(torneo=torneo, jugador=portero).first()
            if est:
                est.goles_contra = anotacion_contra
                est.save()
    else:
        empates = 0

    puntos = victorias * puntos_ganador + derrotas * puntos_perdedor + empates

    clasif.puntos = puntos
    clasif.victorias = victorias
    clasif.empates = empates
    clasif.derrotas = derrotas
    clasif.anotacion_favor = anotacion_favor
    clasif.anotacion_contra = anotacion_contra
    clasif.save()

    
@transaction.atomic
def actualizar_eliminatoria(enfrentamiento: Enfrentamiento):
    if enfrentamiento.ganador is None:
        return HttpResponse( _("No se puede actualizar la eliminatoria sin un ganador definido."), status=400 )

    siguiente = Enfrentamiento.objects.filter(
        eliminatoria=enfrentamiento.eliminatoria, prev_local=enfrentamiento
    ).first()
    es_local = True
    if siguiente is None:
        siguiente = Enfrentamiento.objects.filter(
            eliminatoria=enfrentamiento.eliminatoria, prev_visitante=enfrentamiento
        ).first()
        es_local = False

    if siguiente is None:
        return HttpResponse( _("No se encontró el siguiente enfrentamiento para actualizar."), status=400 )

    equipo_anterior = siguiente.equipo_local if es_local else siguiente.equipo_visitante

    # Si el equipo del siguiente cambia, limpiamos los resultados del siguiente
    # y propagamos la limpieza hacia adelante para no violar el check constraint
    # enfrentamiento_ganador_local_o_visitante.
    if equipo_anterior != enfrentamiento.ganador:
        _limpiar_resultados_y_descendientes(siguiente)

    if es_local:
        siguiente.equipo_local = enfrentamiento.ganador
    else:
        siguiente.equipo_visitante = enfrentamiento.ganador
    siguiente.save()


def _limpiar_resultados_y_descendientes(enfrentamiento: Enfrentamiento):
    tenia_ganador = enfrentamiento.ganador is not None

    enfrentamiento.ganador = None
    enfrentamiento.anotacion_local = None
    enfrentamiento.anotacion_visitante = None
    enfrentamiento.juegos_local_1 = None
    enfrentamiento.juegos_visitante_1 = None
    enfrentamiento.juegos_local_2 = None
    enfrentamiento.juegos_visitante_2 = None
    enfrentamiento.juegos_local_3 = None
    enfrentamiento.juegos_visitante_3 = None
    enfrentamiento.save()

    if not tenia_ganador:
        return

    descendiente = Enfrentamiento.objects.filter(
        eliminatoria=enfrentamiento.eliminatoria, prev_local=enfrentamiento
    ).first()
    desc_es_local = True
    if descendiente is None:
        descendiente = Enfrentamiento.objects.filter(
            eliminatoria=enfrentamiento.eliminatoria, prev_visitante=enfrentamiento
        ).first()
        desc_es_local = False

    if descendiente is None:
        return

    _limpiar_resultados_y_descendientes(descendiente)
    if desc_es_local:
        descendiente.equipo_local = None
    else:
        descendiente.equipo_visitante = None
    descendiente.save()

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

@transaction.atomic
def crear_eliminatoria_tras_liga(torneo: Torneo):
    elim = Eliminatoria.objects.filter(torneo=torneo).first()

    if elim:
        Enfrentamiento.objects.filter(eliminatoria=elim).delete()
        elim.delete()

    
    if torneo.tipo == TipoTorneo.LIGA:
        espacios = sig_potencia_2(torneo.n_equipos_playoffs)
        partidos_ronda = espacios // 2
        rondas = int(log2(espacios))
        directos = espacios - torneo.n_equipos_playoffs
        clasificados = Clasificacion.objects.filter(torneo_equipo__torneo=torneo, posicion__lte=torneo.n_equipos_playoffs).order_by('posicion')
        eliminatoria = Eliminatoria.objects.create(torneo=torneo, rondas=rondas)

    elif torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
        eliminatoria_grupos = EliminatoriaGrupos.objects.filter(torneo=torneo).first()
        n_equipos = eliminatoria_grupos.n_clasificados_grupo * eliminatoria_grupos.n_grupos
        espacios = sig_potencia_2(n_equipos)
        partidos_ronda = espacios // 2
        rondas = int(log2(espacios))
        directos = espacios - n_equipos
        clasificados = Clasificacion.objects.filter(torneo_equipo__torneo=torneo, posicion__lte=eliminatoria_grupos.n_clasificados_grupo).order_by('posicion', '-puntos', '-victorias', 'derrotas', '-anotacion_favor', 'anotacion_contra')
        eliminatoria = Eliminatoria.objects.create(torneo=torneo, rondas=rondas)
        eliminatoria_grupos.eliminatoria = eliminatoria
        eliminatoria_grupos.save()


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



def round_robin(equipos):
    equipos = list(equipos)
    shuffle(equipos)
    n = len(equipos)
    if n < 2:
        return []
    
    if n % 2 == 1:
        equipos.append(None)
        n += 1
    
    jornadas = []

    for j in range(n - 1):
        partidos = []
        for i in range(n // 2):
            local = equipos[i]
            visitante = equipos[n - 1 - i]
            if local is not None and visitante is not None:
                # Para equilibrar un poco alternamos entre local y visitante en cada jornada
                if j % 2 == 0:
                    partidos.append((local, visitante))
                else:
                    partidos.append((visitante, local))

        jornadas.append(partidos)
        equipos = [equipos[0]] + [equipos[-1]] + equipos[1:-1]
    
    return jornadas


def peso_partido(nivel_local, nivel_visitante):
    '''
    Ponderación de partidos segun el nivel de sus equipos
    -Nivel 1 vs Nivel 1: 3 puntos
    -Nivel 1/2 vs Nivel 1/2: 2 puntos
    -Nivel 1/2 vs Nivel 3: 1 punto
    -Resto: 0 puntos
    '''
    if not nivel_local or not nivel_visitante:
        return 0
    
    if nivel_local == 1 and nivel_visitante == 1:
        return 3
    
    if (nivel_local == 1 and nivel_visitante == 2) or (nivel_local == 2 and nivel_visitante == 1):
        return 2
    
    if (nivel_local < 3 and nivel_visitante == 3) or (nivel_local == 3 and nivel_visitante < 3):
        return 1
    
    return 0
    
def reordenar_jornadas(jornadas, niveles_equipos):
    num_jornadas = len(jornadas)
    if num_jornadas < 4:
        return jornadas
    
    puntuaciones = []
    for idx, jornada in enumerate(jornadas):
        puntuacion = 0
        for local, visitante in jornada:
            puntuacion += peso_partido(nivel_local=niveles_equipos.get(local.id), nivel_visitante=niveles_equipos.get(visitante.id))
        puntuaciones.append((idx, puntuacion))


    puntuaciones.sort(key=lambda x: x[1])

    tercio = max(1, num_jornadas // 3)

    faciles = [idx for idx, _ in puntuaciones[:tercio]]
    dificiles = [idx for idx, _ in puntuaciones[-tercio:]]
    medias = [idx for idx, _ in puntuaciones[tercio:num_jornadas-tercio]]

    nuevo_orden_indices = [None] * num_jornadas

    mitad_principio = num_jornadas // 3
    mitad_final = num_jornadas - mitad_principio

    if mitad_final <= mitad_principio:
        mitad_principio = num_jornadas // 2
        mitad_final = mitad_principio + 1

    posiciones_centro = list(range(mitad_principio, mitad_final))

    #Colocamos las dificiles en medio
    if dificiles:
        paso = max(1, len(posiciones_centro) // len(dificiles))
        pos_idx = 0
        for idx_jornada in dificiles:
            if pos_idx >= len(posiciones_centro):
                pos_idx = len(posiciones_centro) - 1
            
            pos = posiciones_centro[pos_idx]
            nuevo_orden_indices[pos] = idx_jornada
            pos_idx += paso

    posiciones_inicio = list(range(0, mitad_principio))
    posiciones_final = list(range(mitad_final, num_jornadas))
    posiciones_extremos = []

    i = 0
    j = len(posiciones_final) - 1
    while i < len(posiciones_inicio) or j >= 0:
        if i < len(posiciones_inicio):
            posiciones_extremos.append(posiciones_inicio[i])
            i += 1
        if j >= 0:
            posiciones_extremos.append(posiciones_final[j])
            j -= 1

    #Metemos los faciles en los extremos
    usados = {idx for idx in nuevo_orden_indices if idx is not None}

    pos_exteriores = 0
    for idx_jornada in faciles:
        if pos_exteriores >= len(posiciones_extremos):
            break

        if idx_jornada not in usados:
            pos = posiciones_extremos[pos_exteriores]
            if nuevo_orden_indices[pos] is None:
                nuevo_orden_indices[pos] = idx_jornada
                usados.add(idx_jornada)
            
            pos_exteriores += 1

    #Los restantes los metemos donde haya hueco, dando preferencia a las medias
    restantes = []
    for idx_jornada in medias + faciles:
        if idx_jornada not in usados:
            restantes.append(idx_jornada)

    for pos in range(num_jornadas):
        if nuevo_orden_indices[pos] is None and restantes:
            idx_jornada = restantes.pop(0)
            nuevo_orden_indices[pos] = idx_jornada
            usados.add(idx_jornada)

    #Por seguridad si quedase algun None en la lista con el nuevo orden
    if None in nuevo_orden_indices:
        faltan = [idx for idx, _ in puntuaciones if idx not in usados]
        for pos in range(num_jornadas):
            if nuevo_orden_indices[pos] is None and faltan:
                nuevo_orden_indices[pos] = faltan.pop(0)

    return [jornadas[idx] for idx in nuevo_orden_indices]
    


    



def generar_liga_aleatorio(torneo: Torneo, ida_vuelta: bool = False):
    torneo_equipos = list(TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo'))
    equipos = [te.equipo for te in torneo_equipos]
    #Borramos por si hubiese enfrentamientos previos
    Enfrentamiento.objects.filter(jornada__torneo=torneo).delete()
    Jornada.objects.filter(torneo=torneo).delete()

    jornadas_ida = round_robin(equipos)

    for i, partidos in enumerate(jornadas_ida, 1):
        jornada = Jornada.objects.create(torneo=torneo, n_jornada=i)

        for local, visitante in partidos:
            Enfrentamiento.objects.create(
                jornada=jornada,
                equipo_local=local,
                equipo_visitante=visitante
            )


    if ida_vuelta:
        fin_ida = len(jornadas_ida)
        for i, partidos in enumerate(jornadas_ida, 1):
            jornada = Jornada.objects.create(torneo=torneo, n_jornada= fin_ida + i)

            for local, visitante in partidos:
                Enfrentamiento.objects.create(
                    jornada=jornada,
                    equipo_local=visitante,
                    equipo_visitante=local
                ) 

    

def generar_liga_personalizado(torneo: Torneo, niveles: dict[int, int], ida_vuelta: bool):
    torneo_equipos = list(TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo'))
    equipos = [te.equipo for te in torneo_equipos]
    #Borramos por si hubiese enfrentamientos previos
    Enfrentamiento.objects.filter(jornada__torneo=torneo).delete()
    Jornada.objects.filter(torneo=torneo).delete()

    jornadas_ida = round_robin(equipos)
    niveles_equipo = {}
    for te in torneo_equipos:
        nivel = te.nivel or niveles.get(te.equipo.id)
        if nivel:
            niveles_equipo[te.equipo.id] = nivel
    
    jornadas_ida = reordenar_jornadas(jornadas_ida, niveles_equipo)

    for i, partidos in enumerate(jornadas_ida, 1):
        jornada = Jornada.objects.create(torneo=torneo, n_jornada=i)

        for local, visitante in partidos:
            Enfrentamiento.objects.create(
                jornada=jornada,
                equipo_local=local,
                equipo_visitante=visitante
            )

    if ida_vuelta:
        fin_ida = len(jornadas_ida)
        for i, partidos in enumerate(jornadas_ida, 1):
            jornada = Jornada.objects.create(torneo=torneo, n_jornada= fin_ida + i)

            for local, visitante in partidos:
                Enfrentamiento.objects.create(
                    jornada=jornada,
                    equipo_local=visitante,
                    equipo_visitante=local
                )

def crear_cuadro_eliminatoria(torneo: Torneo, equipos: list[Equipo]):
    espacios = sig_potencia_2(len(equipos))
    partidos_ronda = espacios // 2
    directos = espacios - len(equipos)
    rondas = int(log2(espacios))

    elim = Eliminatoria.objects.filter(torneo=torneo).first()
    if elim:
        elim.delete()

    eliminatoria = Eliminatoria.objects.create(torneo=torneo, rondas=rondas)

    enfrentamientos = []

    rondas_torneo = RONDAS[-rondas:]

    for i in range(partidos_ronda):
        if i < directos:
            enfrentamientos.append(
                Enfrentamiento.objects.create(ronda=rondas_torneo[0], eliminatoria=eliminatoria, equipo_local=equipos[i], equipo_visitante=None)
            )
        else:
            enfrentamientos.append(
                Enfrentamiento.objects.create(
                    ronda=rondas_torneo[0],
                    eliminatoria=eliminatoria,
                    equipo_local=equipos[i],
                    equipo_visitante=equipos[espacios - i - 1]
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

def generar_eliminatoria_aleatorio(torneo: Torneo):
    torneo_equipos = list(TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo'))
    if len(torneo_equipos) < 2:
        return
    equipos = [te.equipo for te in torneo_equipos]
    shuffle(equipos)
    crear_cuadro_eliminatoria(torneo, equipos)
    

def generar_eliminatoria_personalizado(torneo: Torneo, niveles: dict[int, int]):
    torneo_equipos = list(TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo'))
    if len(torneo_equipos) < 2:
        return
    torneo_equipos.sort(key=lambda te: te.nivel or niveles.get(te.equipo.id, 4))
    equipos = [te.equipo for te in torneo_equipos]
    crear_cuadro_eliminatoria(torneo, equipos) 


def generar_jornadas_fase_grupos(torneo: Torneo, grupos_equipos: list[list], ida_vuelta: bool = False):
    #Borramos primero por si hubiese enfrentamientos y jornadas previas
    Enfrentamiento.objects.filter(jornada__torneo=torneo).delete()
    Jornada.objects.filter(torneo=torneo).delete()

    enfrentamientos_grupo = [round_robin(lista) for lista in grupos_equipos]
    num_jornadas = max((len(s) for s in enfrentamientos_grupo), default=0)

    for jornada_idx in range(num_jornadas):
        jornada = Jornada.objects.create(torneo=torneo, n_jornada=jornada_idx + 1)
        for grupo in enfrentamientos_grupo:
            if jornada_idx < len(grupo):
                partidos = grupo[jornada_idx]
                for local, visitante in partidos:
                    Enfrentamiento.objects.create(
                        jornada=jornada,
                        equipo_local=local,
                        equipo_visitante=visitante
                    )

    if ida_vuelta:
        fin_ida = num_jornadas
        for jornada_idx in range(num_jornadas):
            jornada = Jornada.objects.create(torneo=torneo, n_jornada=fin_ida + jornada_idx + 1)
            for grupo in enfrentamientos_grupo:
                if jornada_idx < len(grupo):
                    partidos = grupo[jornada_idx]
                    for local, visitante in partidos:
                        Enfrentamiento.objects.create(
                            jornada=jornada,
                            equipo_local=visitante,
                            equipo_visitante=local
                        )
    

def generar_fase_grupos_aleatorio(torneo: Torneo, ida_vuelta: bool = False):
    eliminatoria_grupos = EliminatoriaGrupos.objects.filter(torneo=torneo).first()
    if not eliminatoria_grupos:
        return
    
    torneo_equipos = list(TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo'))
    equipos = [te.equipo for te in torneo_equipos]

    shuffle(equipos)
    n_grupos = eliminatoria_grupos.n_grupos
    grupos_equipos = [[] for _ in range(n_grupos)]

    for idx, equipo in enumerate(equipos):
        grupos_equipos[idx % n_grupos].append(equipo)

    nombre_grupos = [chr(ord('A') + i) for i in range(n_grupos)]
    for idx_grupo, lista_equipos in enumerate(grupos_equipos):
        pos = 1
        for equipo in lista_equipos:
            te = TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).first()
            if te:
                Clasificacion.objects.update_or_create(
                    torneo_equipo = te,
                    eliminatoria_grupos = eliminatoria_grupos,
                    grupo = nombre_grupos[idx_grupo],
                    defaults={
                        "posicion": pos,
                        "puntos": 0,
                        "victorias": 0,
                        "empates": 0,
                        "derrotas": 0,
                        "anotacion_favor": 0,
                        "anotacion_contra": 0,
                    }
                )
            pos += 1

    generar_jornadas_fase_grupos(torneo, grupos_equipos, ida_vuelta)

def generar_fase_grupos_personalizado(torneo: Torneo, niveles: dict[int, int], ida_vuelta: bool = False):
    eliminatoria_grupos = EliminatoriaGrupos.objects.filter(torneo=torneo).first()
    if not eliminatoria_grupos:
        return
    
    torneo_equipos = list(TorneoEquipo.objects.filter(torneo=torneo).select_related('equipo'))
    equipos_info = []
    for te in torneo_equipos:
        nivel = te.nivel or niveles.get(te.equipo.id, 4)
        equipos_info.append((te.equipo, nivel))

    equipos_info.sort(key=lambda x: x[1])
    n_grupos = eliminatoria_grupos.n_grupos
    grupos_equipos = [[] for _ in range(n_grupos)]

    for idx, (equipo, nivel) in enumerate(equipos_info):
        grupos_equipos[idx % n_grupos].append(equipo)

    nombre_grupos = [chr(ord('A') + i) for i in range(n_grupos)]
    for idx_grupo, lista_equipos in enumerate(grupos_equipos):
        pos = 1
        for equipo in lista_equipos:
            te = TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).first()
            if te:
                Clasificacion.objects.update_or_create(
                    torneo_equipo = te,
                    eliminatoria_grupos = eliminatoria_grupos,
                    grupo = nombre_grupos[idx_grupo],
                    posicion = pos,
                    puntos = 0,
                    victorias = 0,
                    empates = 0,
                    derrotas = 0,
                    anotacion_favor = 0,
                    anotacion_contra = 0
                )
            pos += 1

    generar_jornadas_fase_grupos(torneo, grupos_equipos, ida_vuelta)
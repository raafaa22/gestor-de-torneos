from django.contrib.auth import get_user_model

from gestor.choices import Deporte, TipoTorneo, TipoRonda
from usuario.models import Administrador, Organizador, Jugador
from equipo.models import Equipo
from torneo.models import Torneo, TorneoEquipo, Clasificacion, Jornada, Eliminatoria, EliminatoriaGrupos
from enfrentamiento.models import Enfrentamiento
from estadisticas.models import EstadisticasFutbol, EstadisticasBaloncesto

User = get_user_model()

CLAVE="tests1234"

def create_user(email="user@example.com", password=CLAVE):
    return User.objects.create_user(username=email, email=email, password=password)

def create_administrador(email="admin@test.com", nombre="Test Admin", password=CLAVE):
    user = create_user(email=email, password=password)
    return Administrador.objects.create(user=user, nombre=nombre)

def create_organizador(email="organizador@test.com", nombre="Test Organizador", password=CLAVE):
    user = create_user(email=email, password=password)
    return Organizador.objects.create(user=user, nombre=nombre)

def create_equipo(
        email="equipo@test.com",
        password=CLAVE,
        nombre="Test Equipo",
        deporte=Deporte.FUTBOL,
):
    user = create_user(email=email, password=password)
    return Equipo.objects.create(user=user, nombre=nombre, deporte=deporte)


def create_jugador(
        email="equipo@test.com",
        password=CLAVE,
        dni="77777777R",
        nombre="Jugador",
        apellidos="Test Prueba",
        equipo=None,
        es_portero=False,
):
    user = create_user(email=email, password=password)
    return Jugador.objects.create(
        user=user,
        dni=dni,
        nombre=nombre,
        apellidos=apellidos,
        equipo=equipo,
        es_portero=es_portero
    )

def create_torneo(
        nombre="Torneo Test",
        organizador=None,
        deporte=Deporte.FUTBOL,
        tipo_torneo=TipoTorneo.LIGA,
        max_equipos=8,
        playoffs=False,
        n_equipos_playoffs=None,
        descenso=False,
        n_equipos_descenso=None
):
    if organizador is None:
        organizador = create_organizador()
    
    return Torneo.objects.create(
        nombre=nombre,
        descripcion="Descripción del torneo de prueba",
        organizador=organizador,
        deporte=deporte,
        tipo_torneo=tipo_torneo,
        max_equipos=max_equipos,
        playoffs=playoffs,
        n_equipos_playoffs=n_equipos_playoffs,
        descenso=descenso,
        n_equipos_descenso=n_equipos_descenso
    )


def create_inscripcion_torneo(
        torneo,
        equipo,
        posicion=1,
        grupo="GENERAL",
        n_grupos=1,
        n_clasificados_grupo=1
):
    te = TorneoEquipo.objects.create(torneo=torneo, equipo=equipo)

    if torneo.tipo_torneo == TipoTorneo.LIGA:
        Clasificacion.objects.create(
            torneo_equipo=te,
            grupo=grupo,
            posicion=posicion,
            puntos=0,
            victorias=0,
            empates=0,
            derrotas=0,
            anotacion_favor=0,
            anotacion_contra=0
        )
    elif torneo.tipo_torneo == TipoTorneo.ELIMINATORIA_GRUPOS:
        EliminatoriaGrupos.objects.create(
            torneo=torneo,
            elminatoria=None,
            n_clasificados_grupo=n_clasificados_grupo,
            n_grupos=n_grupos
        )

    return te


def create_estadisticas_jugadores_torneo(torneo,equipo):
    jugadores = Jugador.objects.filter(equipo=equipo)

    for jugador in jugadores:
        if torneo.deporte == Deporte.FUTBOL:
            EstadisticasFutbol.objects.create(
                torneo=torneo,
                jugador=jugador,
                goles=0,
                asistencias=0,
                goles_contra=0 if jugador.es_portero else None,
            )
        elif torneo.deporte == Deporte.BALONCESTO:
            EstadisticasBaloncesto.objects.create(
                torneo=torneo,
                jugador=jugador,
                puntos=0,
                rebotes=0,
                asistencias=0,
            )

def create_jornada(torneo, n_jornada=1):
    return Jornada.objects.create(torneo=torneo, n_jornada=n_jornada)


def create_enfrentamiento_liga(torneo, equipo_local, equipo_visitante, n_jornada=1):
    jornada = create_jornada(torneo, n_jornada)
    return Enfrentamiento.objects.create(jornada=jornada, equipo_local=equipo_local, equipo_visitante=equipo_visitante)


def create_eliminatoria(torneo, rondas=1):
    return Eliminatoria.objects.create(torneo=torneo, rondas=rondas)

def create_enfrentamiento_eliminatoria(
        eliminatoria,
        ronda=TipoRonda.SEMIFINAL,
        equipo_local=None,
        equipo_visitante=None,
        prev_local=None,
        prev_visitante=None
):
    return Enfrentamiento.objects.create(
        eliminatoria=eliminatoria,
        ronda=ronda,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        prev_local=prev_local,
        prev_visitante=prev_visitante
    )


def create_varios_equipos(cantidad, deporte=Deporte.FUTBOL, prefijo="Equipo"):
    equipos = []
    for i in range(1, cantidad+1):
        equipo = create_equipo(
            email=f"{prefijo.lower()}{i}@test.com",
            nombre=f"{prefijo} {i}",
            deporte=deporte,
        )
        equipos.append(equipo)

    return equipos
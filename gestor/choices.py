from django.db import models
from django.utils.translation import gettext_lazy as _

class Deporte(models.TextChoices):
    FUTBOL = 'FUT', _('Fútbol')
    BALONCESTO = 'BAL', _('Baloncesto')
    PADEL = 'PAD', _('Pádel')

class TipoTorneo(models.TextChoices):
    LIGA = 'LIG', _('Liga')
    ELIMINATORIA = 'ELI', _('Eliminatoria')
    ELIMINATORIA_GRUPOS = 'ELG', _('Eliminatoria con Fase de Grupos')

class TipoRonda(models.TextChoices):
    DIECISEISAVOS = '16AV', _('Dieciseisavos de Final')
    OCTAVOS = '8AV', _('Octavos de Final')
    CUARTOS = 'CUA', _('Cuartos de Final')
    SEMIFINAL = 'SEM', _('Semifinal')
    FINAL = 'FIN', _('Final')
class RolUsuario(models.TextChoices):
    ORGANIZADOR = 'ORG', _('Organizador')
    EQUIPO = 'EQ', _('Equipo')

class TipoUsuario(models.TextChoices):
    ADMINISTRADOR = 'ADM', _('Administrador')
    ORGANIZADOR = 'ORG', _('Organizador')
    EQUIPO = 'EQ', _('Equipo')
    JUGADOR = 'JUG', _('Jugador')

class EstadisticaFutbol(models.TextChoices):
    GOLES = 'GOL', _('Goles')
    ASISTENCIAS = 'ASI', _('Asistencias')

class EstadisticaBaloncesto(models.TextChoices):
    PUNTOS = 'PTS', _('Puntos')
    REBOTES = 'REB', _('Rebotes')
    ASISTENCIAS = 'ASI', _('Asistencias')

class Nivel(models.IntegerChoices):
    NIVEL1 = 1, _('Nivel 1')
    NIVEL2 = 2, _('Nivel 2')
    NIVEL3 = 3, _('Nivel 3')
    NIVEL4 = 4, _('Nivel 4')
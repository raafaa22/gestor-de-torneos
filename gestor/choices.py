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
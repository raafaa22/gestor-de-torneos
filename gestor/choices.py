from django.db import models

class Deporte(models.TextChoices):
    FUTBOL = 'FUT', 'Fútbol'
    BALONCESTO = 'BAL', 'Baloncesto'
    PADEL = 'PAD', 'Pádel'

class TipoTorneo(models.TextChoices):
    LIGA = 'LIG', 'Liga'
    ELIMINATORIA = 'ELI', 'Eliminatoria'
    ELIMINATORIA_GRUPOS = 'ELG', 'Eliminatoria con Fase de Grupos'

class TipoRonda(models.TextChoices):
    DIECISEISAVOS = '16AV', 'Dieciseisavos de Final'
    OCTAVOS = '8AV', 'Octavos de Final'
    CUARTOS = 'CUA', 'Cuartos de Final'
    SEMIFINAL = 'SEM', 'Semifinal'
    FINAL = 'FIN', 'Final'

class RolUsuario(models.TextChoices):
    ORGANIZADOR = 'ORG', 'Organizador'
    EQUIPO = 'EQ', 'Equipo'
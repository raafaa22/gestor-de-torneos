from django.db import models
from django.core.validators import MinValueValidator
from gestor.choices import TipoRonda, EstadisticaFutbol, EstadisticaBaloncesto
from equipo.models import Equipo
from torneo.models import Eliminatoria, Jornada
from usuario.models import Jugador

class Enfrentamiento(models.Model):
    eliminatoria = models.ForeignKey(Eliminatoria, null=True, blank=True, on_delete=models.CASCADE, related_name='enfrentamientos')
    jornada = models.ForeignKey(Jornada, null=True, blank=True, on_delete=models.CASCADE, related_name='enfrentamientos')
    ronda = models.CharField(max_length=4, choices=TipoRonda.choices, null=True, blank=True)
    equipo_local = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_local')
    equipo_visitante = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_visitante')
    ganador = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_ganador')
    anotacion_local = models.PositiveIntegerField(null=True, blank=True)
    anotacion_visitante = models.PositiveIntegerField(null=True, blank=True)
    juegos_local_1 = models.PositiveIntegerField(null=True, blank=True)
    juegos_visitante_1 = models.PositiveIntegerField(null=True, blank=True)
    juegos_local_2 = models.PositiveIntegerField(null=True, blank=True)
    juegos_visitante_2 = models.PositiveIntegerField(null=True, blank=True)
    juegos_local_3 = models.PositiveIntegerField(null=True, blank=True)
    juegos_visitante_3 = models.PositiveIntegerField(null=True, blank=True)
    prev_local = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_siguientes_local')
    prev_visitante = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_siguientes_visitante')

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(eliminatoria__isnull=False, jornada__isnull=True) |
                    models.Q(eliminatoria__isnull=True, jornada__isnull=False)
                ),
                name='enfrentamiento_eliminatoria_o_jornada'
            ),
            models.CheckConstraint(
                check=~models.Q(equipo_local=models.F('equipo_visitante')),
                name='enfrentamiento_equipo_local_distinto_visitante'
            ),
            models.CheckConstraint(
                check=(
                    models.Q(ganador__isnull=True) |
                    models.Q(ganador=models.F('equipo_local')) |
                    models.Q(ganador=models.F('equipo_visitante'))
                ),
                name='enfrentamiento_ganador_local_o_visitante'
            ),
        ]

    def __str__(self):
        return f'{self.equipo_local} vs {self.equipo_visitante}'
    

class GuardadoEnfrentamiento(models.Model):
    enfrentamiento = models.ForeignKey(Enfrentamiento, on_delete=models.CASCADE, related_name='guardados')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='guardados_enfrentamientos')
    estadistica_futbol = models.CharField(max_length=3, choices=EstadisticaFutbol.choices, null=True, blank=True)
    estadistica_baloncesto = models.CharField(max_length=3, choices=EstadisticaBaloncesto.choices, null=True, blank=True)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['enfrentamiento', 'jugador', 'estadistica_futbol', 'estadistica_baloncesto'],
                name='unique_estadistica_enfrentamiento_guardado_jugador_tipo'
            )
        ]


class EstadisticasEnfrentamiento(models.Model):
    enfrentamiento = models.ForeignKey(Enfrentamiento, on_delete=models.CASCADE, related_name='estadisticas')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='estadisticas_enfrentamientos')
    estadistica_futbol = models.CharField(max_length=3, choices=EstadisticaFutbol.choices, null=True, blank=True)
    estadistica_baloncesto = models.CharField(max_length=3, choices=EstadisticaBaloncesto.choices, null=True, blank=True)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['enfrentamiento', 'jugador', 'estadistica_futbol', 'estadistica_baloncesto'],
                name='unique_estadistica_enfrentamiento_jugador_tipo'
            )
        ]

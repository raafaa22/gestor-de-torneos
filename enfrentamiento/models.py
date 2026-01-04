from django.db import models
from gestor.choices import TipoRonda
from equipo.models import Equipo
from torneo.models import Eliminatoria, Jornada

class Enfrentamiento(models.Model):
    eliminatoria = models.ForeignKey(Eliminatoria, null=True, blank=True, on_delete=models.CASCADE, related_name='enfrentamientos')
    jornada = models.ForeignKey(Jornada, null=True, blank=True, on_delete=models.CASCADE, related_name='enfrentamientos')
    ronda = models.CharField(max_length=4, choices=TipoRonda.choices, null=True, blank=True)
    equipo_local = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_local')
    equipo_visitante = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_visitante')
    ganador = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_ganados')
    anotacion_local = models.PositiveIntegerField(null=True, blank=True)
    anotacion_visitante = models.PositiveIntegerField(null=True, blank=True)
    juegos_local_1 = models.PositiveIntegerField(null=True, blank=True)
    juegos_visitante_1 = models.PositiveIntegerField(null=True, blank=True)
    juegos_local_2 = models.PositiveIntegerField(null=True, blank=True)
    juegos_visitante_2 = models.PositiveIntegerField(null=True, blank=True)
    juegos_local_3 = models.PositiveIntegerField(null=True, blank=True)
    juegos_visitante_3 = models.PositiveIntegerField(null=True, blank=True)

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
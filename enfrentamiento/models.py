from django.db import models
from gestor.choices import TipoRonda
from equipo.models import Equipo
from torneo.models import Eliminatoria, Jornada

class Enfrentamiento(models.Model):
    eliminatoria = models.ForeignKey(Eliminatoria, null=True, blank=True, on_delete=models.CASCADE, related_name='enfrentamientos')
    jornada = models.ForeignKey(Jornada, null=True, blank=True, on_delete=models.CASCADE, related_name='enfrentamientos')
    ronda = models.CharField(max_length=3, choices=TipoRonda.choices, null=True, blank=True)
    equipo_local = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_local')
    equipo_visitante = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_visitante')
    ganador = models.ForeignKey(Equipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='enfrentamientos_ganados')
    anotacion_local = models.PositiveIntegerField(null=True, blank=True, default=0)
    anotacion_visitante = models.PositiveIntegerField(null=True, blank=True, default=0)
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
            )
        ]

    def __str__(self):
        return f'{self.equipo_local} vs {self.equipo_visitante}'
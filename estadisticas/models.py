from django.db import models
from torneo.models import Torneo
from usuario.models import Jugador

class EstadisticasFutbol(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE,  related_name='estadisticas_futbol')
    jugador = models.ForeignKey(Jugador, null=False, blank=False, on_delete=models.CASCADE, related_name='estadisticas_futbol')
    goles = models.PositiveIntegerField(null=False, default=0)
    asistencias = models.PositiveIntegerField(null=False, default=0)
    goles_contra = models.PositiveIntegerField(null=True, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['torneo', 'jugador'], name='unique_torneo_jugador_estadisticas_futbol')
        ]

    def __str__(self):
        return f'Estadisticas de {self.jugador.user.username} en {self.torneo.nombre}'
    

class EstadisticasBaloncesto(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE,  related_name='estadisticas_baloncesto')
    jugador = models.ForeignKey(Jugador, null=False, blank=False, on_delete=models.CASCADE, related_name='estadisticas_baloncesto')
    puntos = models.PositiveIntegerField(null=False, default=0)
    rebotes = models.PositiveIntegerField(null=False, default=0)
    asistencias = models.PositiveIntegerField(null=False, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['torneo', 'jugador'], name='unique_torneo_jugador_estadisticas_baloncesto')
        ]

    def __str__(self):
        return f'Estadisticas de {self.jugador.user.username} en {self.torneo.nombre}'


from django.db import models
from gestor.choices import Deporte, TipoTorneo, TipoRonda
from usuario.models import Organizador, Jugador
from equipo.models import Equipo


class Torneo(models.Model):
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=True, blank=True)
    organizador = models.ForeignKey(Organizador, null=False, blank=False, on_delete=models.PROTECT, related_name='torneos')
    ganador = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='torneos_ganados')
    max_equipos = models.PositiveIntegerField(null=False)
    deporte = models.CharField(max_length=3, choices=Deporte.choices, null=False)
    tipo = models.CharField(max_length=3, choices=TipoTorneo.choices, null=False)
    playoffs = models.BooleanField(default=False, null=False)
    n_equipos_playoffs = models.PositiveIntegerField(null=True)
    descenso = models.BooleanField(default=False, null=False)
    n_equipos_descenso = models.PositiveIntegerField(null=True)

    def __str__(self):
        return self.nombre


# Tabla puente entre Torneo y Equipo
class TorneoEquipo(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE, related_name='torneo_equipos')
    equipo = models.ForeignKey(Equipo, null=False, blank=False, on_delete=models.CASCADE, related_name='equipo_torneos')


    # Un equipo no puede estar mas de una vez en el mismo torneo
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['torneo', 'equipo'], name='unique_torneo_equipo')
        ]
    
    def __str__(self):
        return f'{self.equipo.nombre} en {self.torneo.nombre}'
    

class Jornada(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE, related_name='jornadas')
    n_jornada = models.PositiveIntegerField(null=False)

    # Un numero de jornada no puede repetirse en el mismo torneo
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['torneo', 'n_jornada'], name='unique_torneo_n_jornada')
        ]

    def __str__(self):
        return f'Jornada {self.n_jornada} - {self.torneo.nombre}'

class Eliminatoria(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE, related_name='eliminatorias')
    rondas = models.PositiveIntegerField(null=False, default=1, validators=[models.Min(1), models.Max(5)])

    def __str__(self):
        return f'Eliminatoria - {self.torneo.nombre}'
    

class EliminatoriaGrupos(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE, related_name='eliminatoria_grupos')
    eliminatoria = models.ForeignKey(Eliminatoria, null=False, blank=False, on_delete=models.CASCADE, related_name='eliminatoria_grupos')
    n_clasificados_grupo = models.PositiveIntegerField(null=False, validators=[models.Min(1)])
    n_grupos = models.PositiveIntegerField(null=False, validators=[models.Min(1), models.Max(16)])

    def __str__(self):
        return f'Eliminatoria con Fase de Grupos - {self.torneo.nombre}'
    
    
class Clasificacion(models.Model):
    torneo = models.ForeignKey(Torneo, null=False, blank=False, on_delete=models.CASCADE, related_name='clasificaciones')
    equipo = models.ForeignKey(Equipo, null=False, blank=False, on_delete=models.CASCADE, related_name='clasificaciones')
    eliminatoria_grupos = models.ForeignKey(EliminatoriaGrupos, null=True, blank=True, on_delete=models.CASCADE, related_name='clasificaciones')
    posicion = models.PositiveIntegerField(null=False)
    puntos = models.IntegerField(null=False, default=0)
    victorias = models.PositiveIntegerField(null=False, default=0)
    empates = models.PositiveIntegerField(null=False, default=0)
    derrotas = models.PositiveIntegerField(null=False, default=0)
    anotacion_favor = models.PositiveIntegerField(null=False, default=0)
    anotacion_contra = models.PositiveIntegerField(null=False, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['torneo', 'equipo', 'posicion'], name='unique_torneo_equipo_posicion')
        ]

    def __str__(self):
        return f'Clasificacion: {self.equipo.nombre} en {self.torneo.nombre}'
    




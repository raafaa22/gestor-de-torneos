from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from equipo.models import Equipo


class Administrador(models.Model):
    nombre = models.CharField(max_length=100, null=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_perfil')

    def __str__(self):
        return self.nombre



class Organizador(models.Model):
    nombre = models.CharField(max_length=100, null=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organizador_perfil')

    def __str__(self):
        return self.nombre
    

dni_validator = RegexValidator(regex=r"^\d{8}[A-Z]$", message="El DNI debe tener 8 dígitos seguidos de una letra mayúscula.")

class Jugador(models.Model):
    dni = models.CharField(max_length=9, primary_key=True, validators=[dni_validator])
    nombre = models.CharField(max_length=100, null=False)
    apellidos = models.CharField(max_length=150, null=False)
    es_portero = models.BooleanField(default=False, null=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jugador_perfil')
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='jugadores')

    def __str__(self):
        return f'{self.nombre} {self.apellidos}'
    
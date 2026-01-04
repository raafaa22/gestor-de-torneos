from django.db import models
from django.conf import settings
from gestor.choices import Deporte




class Equipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True, null=False)
    deporte = models.CharField(max_length=3, choices=Deporte.choices, null=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipo_perfil')

    def __str__(self):
        return self.nombre
    





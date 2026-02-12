from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from .models import EstadisticasEnfrentamiento

from usuario.models import Jugador
from gestor.choices import EstadisticaFutbol, EstadisticaBaloncesto

class EstadisticasEnfrentamientoForm(forms.ModelForm):
    tipo = forms.ChoiceField(label=_('Estadística'))

    class Meta:
        model = EstadisticasEnfrentamiento
        fields = ['jugador', 'cantidad']


    def __init__(self, *args, torneo=None, equipo=None, enfrentamiento=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.torneo = torneo
        self.equipo = equipo
        self.enfrentamiento = enfrentamiento
        
        if equipo is not None:
            self.fields['jugador'].queryset = Jugador.objects.filter(equipo=equipo)
        else:
            self.fields['jugador'].queryset = Jugador.objects.none()

        if torneo is not None:
            if torneo.deporte == 'FUT':
                self.fields['tipo'].choices = EstadisticaFutbol.choices
            elif torneo.deporte == 'BAL':
                self.fields['tipo'].choices = EstadisticaBaloncesto.choices
            else:
                self.fields['tipo'].choices = []
        else:
            self.fields['tipo'].choices = []

        self.fields['cantidad'].min_value = 1

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and cantidad < 1:
            raise forms.ValidationError(_('La cantidad debe ser al menos 1.'))
        return cantidad
    
    def clean(self):
        cleaned = super().clean()

        if not self.torneo or not self.equipo or not self.enfrentamiento:
            return cleaned
        
        jugador = cleaned.get("jugador")
        tipo = cleaned.get("tipo")
        cantidad = cleaned.get("cantidad")

        if not jugador or not tipo or not cantidad:
            return cleaned
        
        existe = None
        
        if self.torneo.deporte == 'FUT':
            existe = EstadisticasEnfrentamiento.objects.filter(enfrentamiento=self.enfrentamiento, jugador=jugador, estadistica_futbol=tipo).exists()
        elif self.torneo.deporte == 'BAL':
            existe = EstadisticasEnfrentamiento.objects.filter(enfrentamiento=self.enfrentamiento, jugador=jugador, estadistica_baloncesto=tipo).exists()
        
        if existe:
            raise forms.ValidationError(_('Ya existe una estadística de este tipo para el jugador en este enfrentamiento.'))
        
        if tipo == 'ASI' and self.torneo.deporte == 'FUT':
            if jugador.equipo == self.enfrentamiento.equipo_local:
                anotacion = self.enfrentamiento.anotacion_local
            else:
                anotacion = self.enfrentamiento.anotacion_visitante

            if anotacion <= 0 or anotacion is None:
                raise forms.ValidationError(_('No se pueden asignar asistencias si el equipo no ha anotado ningún gol.'))
            else:
                asistencias_totales = EstadisticasEnfrentamiento.objects.filter(
                    enfrentamiento=self.enfrentamiento,
                    estadistica_futbol="ASI",
                    jugador__equipo=self.equipo,
                ).aggregate(total=Sum("cantidad"))["total"] or 0
                
                if asistencias_totales + cantidad > anotacion:
                    raise forms.ValidationError(_('El número total de asistencias no puede superar el número de goles anotados por el equipo.'))
                
        elif tipo == 'ASI' and self.torneo.deporte == 'BAL':
            if jugador.equipo == self.enfrentamiento.equipo_local:
                anotacion = self.enfrentamiento.anotacion_local
            else:
                anotacion = self.enfrentamiento.anotacion_visitante

                if anotacion <= 1 or anotacion is None:
                    raise forms.ValidationError(_('No se pueden asignar asistencias si el equipo no ha anotado ningún tiro de campo.'))
                else:
                    asistencias_totales = EstadisticasEnfrentamiento.objects.filter(
                        enfrentamiento=self.enfrentamiento,
                        estadistica_baloncesto="ASI",
                        jugador__equipo=self.equipo,
                    ).aggregate(total=Sum("cantidad"))["total"] or 0

                    if (asistencias_totales + cantidad) * 2 > anotacion:
                        raise forms.ValidationError(_('El número total de asistencias no puede superar el número de goles anotados por el equipo.'))
                    
        return cleaned
    

    def save(self, commit=True):
        if not self.enfrentamiento:
            raise ValueError("No se puede guardar la estadística sin un enfrentamiento asociado.")
        
        estadistica = super().save(commit=False)
        estadistica.enfrentamiento = self.enfrentamiento
        if self.torneo.deporte == 'FUT':
            estadistica.estadistica_futbol = self.cleaned_data.get('tipo')
            estadistica.estadistica_baloncesto = None
        elif self.torneo.deporte == 'BAL':
            estadistica.estadistica_baloncesto = self.cleaned_data.get('tipo')
            estadistica.estadistica_futbol = None

        if commit:
            estadistica.save()
            
        return estadistica
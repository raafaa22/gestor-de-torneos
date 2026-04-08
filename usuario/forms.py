from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
import random

from usuario.models import Administrador, Organizador, Jugador
from equipo.models import Equipo
from torneo.models import TorneoEquipo
from estadisticas.models import EstadisticasFutbol, EstadisticasBaloncesto
from gestor.choices import Deporte



User = get_user_model()


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label= _('Correo Electrónico'))

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields.pop('username', None)

        self.fields['email'].label = _("Correo Electrónico")
        self.fields['password1'].label = _("Contraseña")
        self.fields['password2'].label = _("Repite la contraseña")
        self.fields['password2'].help_text = _("Debe coincidir con la contraseña anterior.")

    
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise ValidationError(_("Ya existe una cuenta con este correo electrónico."))
        
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email'].strip().lower()
        user.username = email
        user.email = email

        if commit:
            user.save()
        
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError(_("El correo es obligatorio."))
        
        usuario = User.objects.filter(email__iexact=email) | User.objects.filter(username__iexact=email)
        if self.instance and self.instance.pk:
            usuario = usuario.exclude(pk=self.instance.pk)

        if usuario.exists():
            raise ValidationError(_("Ya existe una cuenta con este correo electrónico."))
        
        return email
    

    def save(self, commit = True):
        usuario = super().save(commit=False)
        email = self.cleaned_data.get("email").strip().lower()
        usuario.username = usuario.email
        if commit:
            usuario.save()
            
        return usuario
    

class OrganizadorForm(forms.ModelForm):
    class Meta:
        model = Organizador
        fields = ['nombre']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].label = _("Nombre")

class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre', 'deporte']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].label = _("Nombre")
        self.fields['deporte'].label = _("Deporte")


class AdministradorForm(forms.ModelForm):
    class Meta:
        model = Administrador
        fields = ["nombre"]
        labels = {
            "nombre": _("Nombre"),
        }

class JugadorForm(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ["dni", "nombre", "apellidos", "equipo", "es_portero"]
        labels = {
            "dni": _("DNI"),
            "nombre": _("Nombre"),
            "apellidos": _("Apellidos"),
            "equipo": _("Equipo"),
            "es_portero": _("Es portero"),
        }

    def __init__(self, *args, equipo=None, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipo = equipo
        self.is_admin = is_admin
        
        self._equipo_original = self.instance.equipo if self.instance.pk else None

        if self.instance and self.instance.pk:
            self.fields["dni"].disabled = True
            
            if not equipo and self.instance.equipo:
                self.equipo = self.instance.equipo


        if not is_admin:
            self.fields.pop("equipo", None)

        
        self._update_es_portero_field()

    def _update_es_portero_field(self):
        """Actualiza la visibilidad del campo es_portero según el equipo"""
        equipo = None

        if self.is_bound:

            equipo_id = self.data.get("equipo")
            if equipo_id:
                try:
                    equipo = Equipo.objects.get(id=equipo_id)
                except Equipo.DoesNotExist:
                    equipo = None
            else:
                equipo = self.equipo or (self.instance.equipo if self.instance.pk else None)
        else:

            equipo = self.equipo or (self.instance.equipo if self.instance.pk else None)

        if not equipo or equipo.deporte != Deporte.FUTBOL:
            self.fields.pop("es_portero", None)

    def clean(self):
        cleaned = super().clean()
        return cleaned

    def save(self, commit=True):
        jugador = super().save(commit=False)

        
        if not self.is_admin and self.equipo:
            jugador.equipo = self.equipo

        equipo_anterior = self._equipo_original
        era_portero = self.instance.es_portero if self.instance.pk else False
        equipo_nuevo = jugador.equipo

        if equipo_nuevo and equipo_nuevo.deporte != Deporte.FUTBOL:
            jugador.es_portero = False

        if commit:
            
            if self.instance.pk and equipo_anterior != equipo_nuevo:
                
                if era_portero and equipo_anterior and equipo_anterior.deporte == Deporte.FUTBOL:
                
                    otros_jugadores = Jugador.objects.filter(
                        equipo=equipo_anterior
                    ).exclude(dni=jugador.dni)

                    if otros_jugadores.exists():
                        nuevo_portero = random.choice(list(otros_jugadores))
                        Jugador.objects.filter(dni=nuevo_portero.dni).update(es_portero=True)

                if equipo_anterior:
                    
                    torneos_anteriores = TorneoEquipo.objects.filter(equipo=equipo_anterior)
                    for te in torneos_anteriores:
                        if te.torneo.deporte == Deporte.FUTBOL:
                            EstadisticasFutbol.objects.filter(jugador=jugador, torneo=te.torneo).delete()
                        else:
                            EstadisticasBaloncesto.objects.filter(jugador=jugador, torneo=te.torneo).delete()

                
                if equipo_nuevo:
                    torneos_nuevos = TorneoEquipo.objects.filter(equipo=equipo_nuevo)
                    for te in torneos_nuevos:
                        if te.torneo.deporte == Deporte.FUTBOL:
                            EstadisticasFutbol.objects.get_or_create(
                                jugador=jugador,
                                torneo=te.torneo,
                                defaults={'goles': 0, 'asistencias': 0, 'goles_contra': None if not jugador.es_portero else 0}
                            )
                        else:
                            EstadisticasBaloncesto.objects.get_or_create(
                                jugador=jugador,
                                torneo=te.torneo,
                                defaults={'puntos': 0, 'rebotes': 0, 'asistencias': 0}
                            )

            jugador.save()

        return jugador

    def clean_dni(self):
        if self.instance and self.instance.pk:
            return self.instance.dni

        dni = (self.cleaned_data.get("dni") or "").strip().upper()
        return dni

class EmailAuthenticationForm(AuthenticationForm):
    
    def __init__(self, request = ..., *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields['username'].label = _("Correo Electrónico")
        self.fields['username'].widget.attrs.update({'autocomplete': 'email'})
        self.fields['username'].widget.attrs.update({'placeholder': _("Correo Electrónico")})
        self.fields['password'].widget.attrs.update({'placeholder': _("Contraseña")})
        self.fields['password'].widget.attrs.update({'autocomplete': 'current-password'})

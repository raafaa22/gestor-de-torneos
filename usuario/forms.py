from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm

from usuario.models import Administrador, Organizador, Jugador
from equipo.models import Equipo



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
        fields = ["dni", "nombre", "apellidos", "es_portero"]
        labels = {
            "dni": _("DNI"),
            "nombre": _("Nombre"),
            "apellidos": _("Apellidos"),
            "es_portero": _("Es portero"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["dni"].disabled = True

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

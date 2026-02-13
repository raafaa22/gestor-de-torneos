from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Torneo
from gestor.choices import TipoTorneo
from usuario.models import Organizador, Administrador






class CrearTorneoForm(forms.ModelForm):
    organizador = forms.ModelChoiceField(
        queryset=Organizador.objects.all(),
        label=_('Organizador'),
        required=True,
    )
    class Meta:
        model = Torneo
        fields = ['organizador','nombre', 'descripcion', 'max_equipos', 'deporte', 'tipo', 'playoffs', 'n_equipos_playoffs', 'descenso', 'n_equipos_descenso']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'playoffs': _('Marcar si el torneo es una liga y se quiere que haya una fase eliminatoria que decida al campeón, con el número de equipos especificado abajo.'),
            'descenso': _('Marcar si el torneo es una liga y se quiere que haya descenso, con el número de equipos especificado abajo.'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        self.fields['nombre'].label = _('Nombre del Torneo')
        self.fields['descripcion'].label = _('Descripción')
        self.fields['max_equipos'].label = _('Número máximo de equipos')
        self.fields['deporte'].label = _('Deporte')
        self.fields['tipo'].label = _('Tipo de Torneo')
        self.fields['playoffs'].label = _('Play-offs')
        self.fields['n_equipos_playoffs'].label = _('Número de equipos en play-offs')
        self.fields['descenso'].label = _('Descenso')
        self.fields['n_equipos_descenso'].label = _('Número de equipos en descenso')

        self.fields["n_equipos_playoffs"].required = False
        self.fields["n_equipos_descenso"].required = False



        if Organizador.objects.filter(user=user).exists():
            self.fields.pop('organizador')

    
    def clean(self):
        cleaned = super().clean()

        max_eq = cleaned.get('max_equipos')

        if cleaned.get('playoffs'):
            n_eq_playoffs = cleaned.get('n_equipos_playoffs')
            if n_eq_playoffs is None:
                self.add_error('n_equipos_playoffs', _('Debe especificar el número de equipos en play-offs si ha marcado que hay play-offs.'))
            elif n_eq_playoffs > max_eq:
                self.add_error('n_equipos_playoffs', _('El número de equipos en play-offs no puede ser mayor que el número máximo de equipos del torneo.'))
            elif n_eq_playoffs > 32:
                self.add_error('n_equipos_playoffs', _('El número de equipos en play-offs no puede ser mayor que 32 ya que como máximo puede haber 5 rondas en una eliminatoria.'))
            elif n_eq_playoffs < 2:
                self.add_error('n_equipos_playoffs', _('El número de equipos en play-offs no puede ser menor que 2.'))

        else:
            cleaned['n_equipos_playoffs'] = None

        if cleaned.get('descenso'):
            n_eq_descenso = cleaned.get('n_equipos_descenso')
            if n_eq_descenso is None:
                self.add_error('n_equipos_descenso', _('Debe especificar el número de equipos en descenso si ha marcado que hay descenso.'))
            elif n_eq_descenso > max_eq:
                self.add_error('n_equipos_descenso', _('El número de equipos en descenso no puede ser mayor que el número máximo de equipos del torneo.'))
        else:
            cleaned['n_equipos_descenso'] = None

        if cleaned.get('playoffs') and cleaned.get('descenso'):
            n_eq_playoffs = cleaned.get('n_equipos_playoffs')
            n_eq_descenso = cleaned.get('n_equipos_descenso')
            if n_eq_playoffs + n_eq_descenso > max_eq:
                self.add_error('n_equipos_descenso', _('La suma de equipos en play-offs y en descenso no puede ser mayor que el número máximo de equipos del torneo.'))

        return cleaned
    

    def save(self, commit=True):
        torneo = super().save(commit=False)

        if Organizador.objects.filter(user=self.user).exists():
            torneo.organizador = Organizador.objects.get(user=self.user)

        if commit:
            torneo.save()

        return torneo


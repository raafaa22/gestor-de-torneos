from django import forms
from django.utils.translation import gettext_lazy as _
from math import log2

from .models import Torneo, EliminatoriaGrupos, TorneoEquipo, Jornada, Eliminatoria, Clasificacion
from gestor.choices import TipoTorneo
from usuario.models import Organizador, Administrador






class CrearTorneoForm(forms.ModelForm):
    organizador = forms.ModelChoiceField(
        queryset=Organizador.objects.all(),
        label=_('Organizador'),
        required=True,
    )

    n_grupos = forms.IntegerField(
        label = _('Número de grupos'),
        required=False,
        min_value=1,
        max_value=32,
    )

    n_clasificados_grupo = forms.IntegerField(
        label = _('Clasificados por grupo'),
        required=False,
        min_value=1,
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

       
        self._tipo_original = self.instance.tipo if self.instance and self.instance.pk else None

        if self.instance and self.instance.pk:
            eg = EliminatoriaGrupos.objects.filter(torneo=self.instance).first()
            if eg:
                self.fields['n_grupos'].initial = eg.n_grupos
                self.fields['n_clasificados_grupo'].initial = eg.n_clasificados_grupo


            self.fields['deporte'].disabled = True

            from equipo.views import torneo_empezado
            if torneo_empezado(self.instance):
                self.fields['tipo'].disabled = True

        if Organizador.objects.filter(user=user).exists():
            self.fields.pop('organizador')

    
    def clean(self):
        cleaned = super().clean()

        max_eq = cleaned.get('max_equipos')

        if max_eq is not None and max_eq < 2:
            self.add_error('max_equipos', _('El número máximo de equipos no puede ser menor que 2.'))

        if max_eq is not None and self.instance and self.instance.pk:
            inscritos = TorneoEquipo.objects.filter(torneo=self.instance).count()
            if max_eq < inscritos:
                self.add_error('max_equipos', _(
                    'El número máximo de equipos no puede ser menor que el número de equipos ya inscritos (%(n)s).'
                ) % {'n': inscritos})

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

        if cleaned.get('tipo') == TipoTorneo.ELIMINATORIA_GRUPOS:
            n_grupos = cleaned.get('n_grupos')
            n_clas = cleaned.get('n_clasificados_grupo')
            

            if not n_grupos:
                self.add_error('n_grupos', _('Se debe indicar el número de grupos.'))
                return cleaned
            if not n_clas:
                self.add_error('n_clasificados_grupo', _('Se debe indicar cuántos equipos se clasifican por grupo.'))
                return cleaned

            if max_eq and (max_eq % n_grupos != 0):
                self.add_error('n_grupos', _('El número máximo de equipos debe ser divisible entre el número de grupos (para que los grupos tengan el mismo tamaño).'))

            if max_eq:
                equipos_por_grupo = max_eq // n_grupos
                if n_clas > equipos_por_grupo:
                    self.add_error('n_clasificados_grupo', _('No pueden clasificarse más equipos de los que hay en cada grupo.'))

            total_clasificados = n_grupos * n_clas
            if total_clasificados < 2:
                self.add_error('n_clasificados_grupo', _('Debe haber al menos 2 clasificados en total para crear eliminatoria.'))
            if total_clasificados > 32:
                self.add_error('n_clasificados_grupo', _('El total de clasificados no puede superar 32 (máximo 5 rondas).'))

        else:
            cleaned['n_grupos'] = None
            cleaned['n_clasificados_grupo'] = None 

        return cleaned
    

    def save(self, commit=True):
        tipo_cambiado = (
            self._tipo_original is not None
            and self.cleaned_data.get('tipo') != self._tipo_original
        )

        torneo = super().save(commit=False)

        if Organizador.objects.filter(user=self.user).exists():
            torneo.organizador = Organizador.objects.get(user=self.user)

        if commit:
            torneo.save()

        if tipo_cambiado and commit:
            # Limpieza de la estructura anterior: el torneo no había empezado, así que
            # podemos resetear jornadas/eliminatorias/clasificaciones para que la nueva
            # estructura se pueda generar limpia. Los TorneoEquipo (inscripciones) se conservan.
            #
            # Borramos primero los Enfrentamiento explícitamente: el modelo tiene un
            # CHECK (eliminatoria_id IS NOT NULL OR jornada_id IS NOT NULL), y el
            # cascade delete de Django puede hacer un UPDATE intermedio que viola
            # ese constraint en MySQL.
            from django.db.models import Q
            from enfrentamiento.models import Enfrentamiento
            Enfrentamiento.objects.filter(
                Q(jornada__torneo=torneo) | Q(eliminatoria__torneo=torneo)
            ).delete()
            Clasificacion.objects.filter(torneo_equipo__torneo=torneo).delete()
            EliminatoriaGrupos.objects.filter(torneo=torneo).delete()
            Jornada.objects.filter(torneo=torneo).delete()
            Eliminatoria.objects.filter(torneo=torneo).delete()

            # Si el nuevo tipo es LIGA, recreamos la clasificación para los equipos ya
            # inscritos (el alta_equipo_torneo solo la crea al inscribir, no al cambiar
            # de tipo).
            if torneo.tipo == TipoTorneo.LIGA:
                for idx, te in enumerate(
                    TorneoEquipo.objects.filter(torneo=torneo).order_by('id'),
                    start=1,
                ):
                    Clasificacion.objects.create(
                        torneo_equipo=te,
                        grupo="GENERAL",
                        posicion=idx,
                        puntos=0,
                        victorias=0,
                        empates=0,
                        derrotas=0,
                        anotacion_favor=0,
                        anotacion_contra=0,
                    )

        if torneo.tipo == TipoTorneo.ELIMINATORIA_GRUPOS:
            n_grupos = self.cleaned_data['n_grupos']
            clasificados = self.cleaned_data['n_clasificados_grupo']

            
            eg = EliminatoriaGrupos.objects.filter(torneo=torneo).first()
            if eg:
                eg.n_grupos = n_grupos
                eg.n_clasificados_grupo = clasificados
                eg.save()
            else:
                EliminatoriaGrupos.objects.create(
                    torneo=torneo,
                    n_grupos=n_grupos,
                    n_clasificados_grupo=clasificados
                )

        return torneo


from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.models import ProtectedError
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from django.db import transaction

from gestor.choices import RolUsuario, TipoUsuario, Deporte
from torneo.models import Torneo, TorneoEquipo
from estadisticas.models import EstadisticasFutbol, EstadisticasBaloncesto
from .forms import UserRegisterForm, OrganizadorForm, EquipoForm, EmailAuthenticationForm, AdministradorForm, JugadorForm, UserUpdateForm
from .models import Organizador, Administrador, Jugador
from equipo.models import Equipo
from torneo.views import tipo_usuario
from enfrentamiento.models import Enfrentamiento


ROL_CHOICES = [
    RolUsuario.ORGANIZADOR,
    RolUsuario.EQUIPO,
]



def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok"}, status=200)
    except Exception:
        return JsonResponse({"status": "error"}, status=503)

def registro(request):
    if request.user.is_authenticated:
        return redirect(post_login(request.user))

    rol = RolUsuario.ORGANIZADOR   

    if request.method == 'POST':
        rol = request.POST.get('rol', RolUsuario.ORGANIZADOR)

        user_form = UserRegisterForm(request.POST)
        org_form = OrganizadorForm(request.POST, prefix='org')
        eq_form = EquipoForm(request.POST, prefix='eq')

        if rol == RolUsuario.ORGANIZADOR:
            if user_form.is_valid() and org_form.is_valid():
                user = user_form.save()
                organizador = org_form.save(commit=False)
                organizador.user = user
                organizador.save()
                return redirect('usuario:login')
        elif rol == RolUsuario.EQUIPO:
            if user_form.is_valid() and eq_form.is_valid():
                user = user_form.save()
                equipo = eq_form.save(commit=False)
                equipo.user = user
                equipo.save()
                return redirect('usuario:login')
    else:
        user_form = UserRegisterForm()
        org_form = OrganizadorForm(prefix='org')
        eq_form = EquipoForm(prefix='eq')
    
    return render(request, 'usuario/registro.html', {
        'user_form': user_form,
        'org_form': org_form,
        'eq_form': eq_form,
        'rol': rol,
        'rol_choices': ROL_CHOICES,
    })
            


def login(request):
    if request.user.is_authenticated:
        return redirect(post_login(request.user))
    
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            
           
            try:
                jugador = Jugador.objects.get(user=user)
                if jugador.tiene_password_por_defecto:
                    return redirect('usuario:cambiar_password_obligatorio')
            except Jugador.DoesNotExist:
                pass
            
            return redirect(post_login(user))
    else:
        form = EmailAuthenticationForm()

    return render(request, 'usuario/login.html', {
        'form': form
    })

@require_POST
@login_required
def logout(request):
    auth_logout(request)
    return redirect('usuario:login')

def post_login(user):

    if Administrador.objects.filter(user=user).exists():
        return 'usuario:administrador'
    elif Organizador.objects.filter(user=user).exists():
        return 'torneo:organizador'
    elif Jugador.objects.filter(user=user).exists():
        return 'torneo:jugador'
    elif Equipo.objects.filter(user=user).exists():
        return 'equipo:dashboard'


@login_required
def home(request):
    return redirect(post_login(request.user))


@login_required
def perfil(request):
    usuario = request.user
    tipo = tipo_usuario(usuario)

    if tipo == TipoUsuario.ADMINISTRADOR:
        rol_instance = Administrador.objects.get(user=usuario)
        RolForm = AdministradorForm
    elif tipo == TipoUsuario.ORGANIZADOR:
        rol_instance = Organizador.objects.get(user=usuario)
        RolForm = OrganizadorForm
    elif tipo == TipoUsuario.JUGADOR:
        rol_instance = Jugador.objects.get(user=usuario)
        RolForm = JugadorForm
    elif tipo == TipoUsuario.EQUIPO:
        rol_instance = Equipo.objects.get(user=usuario)
        RolForm = EquipoForm
    else:
        rol_instance = None
        RolForm = None

    user_form = UserUpdateForm(instance=usuario)
    if RolForm == JugadorForm:
        rol_form = RolForm(instance=rol_instance, equipo=rol_instance.equipo, is_admin=False) if RolForm else None
    else:
        rol_form = RolForm(instance=rol_instance) if RolForm else None
    clave_form = PasswordChangeForm(user=usuario)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'datos':
            user_form = UserUpdateForm(request.POST, instance=usuario)
            if RolForm == JugadorForm:
                rol_form = RolForm(request.POST, instance=rol_instance, equipo=rol_instance.equipo, is_admin=False) if RolForm else None
            else:
                rol_form = RolForm(request.POST, instance=rol_instance) if RolForm else None
            forms_validos = user_form.is_valid() and (rol_form is None or rol_form.is_valid())
            if forms_validos:
                user_form.save()
                if rol_form:
                    rol_form.save()
                return redirect('usuario:home')

        elif accion == 'clave':
            clave_form = PasswordChangeForm(user=usuario, data=request.POST)
            if clave_form.is_valid():
                clave_form.save()
                update_session_auth_hash(request, usuario)
                return redirect('usuario:home')

    return render(request, 'usuario/perfil.html', {
        'user_form': user_form,
        'rol_form': rol_form,
        'clave_form': clave_form,
    })


@login_required
def admin_dashboard(request):
    usuario = request.user
    if not Administrador.objects.filter(user=usuario).exists():
        return HttpResponseBadRequest(_("No tienes permiso para acceder a esta página."))
    
    torneos = Torneo.objects.all()
    return render(request, 'usuario/admin_dashboard.html', {'torneos': torneos})


@login_required
def usuarios(request):
    usuario = request.user
    if not Administrador.objects.filter(user=usuario).exists():
        return HttpResponseBadRequest(_("No tienes permiso para acceder a esta página."))
    
    organizadores = list(Organizador.objects.all())
    equipos = list(Equipo.objects.all())
    jugadores = list(Jugador.objects.all())

    for o in organizadores:
        o.tipo = TipoUsuario.ORGANIZADOR.label
    for e in equipos:
        e.tipo = TipoUsuario.EQUIPO.label
    for j in jugadores:
        j.tipo = TipoUsuario.JUGADOR.label

    usuarios_listado = organizadores + equipos + jugadores
    return render(request, 'usuario/listado_usuarios.html', {'usuarios': usuarios_listado})


@login_required
@require_POST
def borrar_usuario(request, usuario_id: int):
    admin = request.user
    if not Administrador.objects.filter(user=admin).exists():
        return HttpResponseBadRequest(_("No tienes permiso para acceder a esta página."))

    usuario = get_object_or_404(User, id=usuario_id)

    if usuario == admin:
        messages.error(request, _("No puedes eliminar tu propio usuario."))
        return redirect('usuario:listado_usuarios')

    try:
        organizador = Organizador.objects.filter(user=usuario).first()
        if organizador:
            torneos = Torneo.objects.filter(organizador=organizador)
            
            for torneo in torneos:
                Enfrentamiento.objects.filter(
                    eliminatoria__torneo=torneo
                ).delete()
                Enfrentamiento.objects.filter(
                    jornada__torneo=torneo
                ).delete()
            torneos.delete()
        usuario.delete()
    except ProtectedError:
        messages.error(request, _("No se puede eliminar este organizador porque tiene torneos asociados."))

    return redirect('usuario:listado_usuarios')

@login_required
def editar_usuario(request, usuario_id : int):
    admin = request.user
    if not Administrador.objects.filter(user=admin).exists():
        return HttpResponseBadRequest(_("No tienes permiso para acceder a esta página."))

    usuario = get_object_or_404(User, id=usuario_id)
    organizador = Organizador.objects.filter(user=usuario).first()
    if organizador:
        RolForm = AdministradorForm
        rol_instance = organizador
        rol_form = RolForm(instance=rol_instance)
        user_form = UserUpdateForm(instance=usuario)
    else:
        equipo = Equipo.objects.filter(user=usuario).first()
        if equipo:
            RolForm = EquipoForm
            rol_instance = equipo
            rol_form = RolForm(instance=rol_instance)
            user_form = UserUpdateForm(instance=usuario)
        else:
            jugador = Jugador.objects.filter(user=usuario).first()
            if jugador:
                RolForm = JugadorForm
                rol_instance = jugador
                rol_form = RolForm(instance=rol_instance, equipo=jugador.equipo, is_admin=True)
                user_form = UserUpdateForm(instance=usuario)
            else:
                return HttpResponseBadRequest(_("Usuario no encontrado o sin rol asignado."))


    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=usuario)
        if isinstance(rol_instance, Jugador):
            rol_form = RolForm(request.POST, instance=rol_instance, equipo=rol_instance.equipo, is_admin=True) if RolForm else None
        else:
            rol_form = RolForm(request.POST, instance=rol_instance) if RolForm else None
        forms_validos = user_form.is_valid() and (rol_form is None or rol_form.is_valid())
        if forms_validos:
            user_form.save()
            if rol_form:
                rol_form.save()
            return redirect('usuario:listado_usuarios')

    return render(request, 'usuario/editar_usuario.html', {'user_form': user_form, 'rol_form': rol_form, 'usuario': rol_instance})

@login_required
@transaction.atomic
def crear_usuario(request):
    admin = request.user
    if not Administrador.objects.filter(user=admin).exists():
        return HttpResponseBadRequest(_("No tienes permiso para acceder a esta página."))

    rol_choices = [TipoUsuario.ORGANIZADOR, TipoUsuario.EQUIPO, TipoUsuario.JUGADOR]
    equipos = Equipo.objects.exclude(deporte=Deporte.PADEL)

    rol = TipoUsuario.ORGANIZADOR
    user_form = UserRegisterForm()
    org_form = OrganizadorForm(prefix='org')
    eq_form = EquipoForm(prefix='eq')
    jugador_form = JugadorForm(equipo=None, is_admin=True)
    selected_equipo_id = None

    if request.method == 'POST':
        rol = request.POST.get('rol', TipoUsuario.ORGANIZADOR)
        user_form = UserRegisterForm(request.POST)

        if rol == TipoUsuario.ORGANIZADOR:
            org_form = OrganizadorForm(request.POST, prefix='org')
            if user_form.is_valid() and org_form.is_valid():
                user = user_form.save()
                organizador = org_form.save(commit=False)
                organizador.user = user
                organizador.save()
                return redirect('usuario:listado_usuarios')

        elif rol == TipoUsuario.EQUIPO:
            eq_form = EquipoForm(request.POST, prefix='eq')
            if user_form.is_valid() and eq_form.is_valid():
                user = user_form.save()
                equipo = eq_form.save(commit=False)
                equipo.user = user
                equipo.save()
                return redirect('usuario:listado_usuarios')

        elif rol == TipoUsuario.JUGADOR:
            selected_equipo_id = request.POST.get('equipo_jugador')
            equipo = get_object_or_404(Equipo, id=selected_equipo_id)
            jugador_form = JugadorForm(request.POST, equipo=equipo, is_admin=True)

            if user_form.is_valid() and jugador_form.is_valid():
                user = user_form.save()

                es_portero_nuevo = equipo.deporte == Deporte.FUTBOL and jugador_form.cleaned_data.get("es_portero")

                antiguo_portero = None
                if es_portero_nuevo:
                    antiguo_portero = Jugador.objects.filter(equipo=equipo, es_portero=True).first()
                    Jugador.objects.filter(equipo=equipo, es_portero=True).update(es_portero=False)

                jugador = jugador_form.save(commit=False)
                jugador.user = user
                jugador.equipo = equipo
                jugador.save()

                for te in TorneoEquipo.objects.filter(equipo=equipo):
                    if te.torneo.deporte == Deporte.FUTBOL:
                        EstadisticasFutbol.objects.create(jugador=jugador, torneo=te.torneo, goles=0, asistencias=0)
                    elif te.torneo.deporte == Deporte.BALONCESTO:
                        EstadisticasBaloncesto.objects.create(jugador=jugador, torneo=te.torneo, puntos=0, rebotes=0, asistencias=0)

                if es_portero_nuevo and antiguo_portero:
                    for est in EstadisticasFutbol.objects.filter(jugador=antiguo_portero):
                        EstadisticasFutbol.objects.filter(jugador=jugador, torneo=est.torneo).update(goles_contra=est.goles_contra)
                    EstadisticasFutbol.objects.filter(jugador=antiguo_portero).update(goles_contra=None)

                return redirect('usuario:listado_usuarios')

    return render(request, 'usuario/crear_usuario.html', {
        'user_form': user_form,
        'org_form': org_form,
        'eq_form': eq_form,
        'jugador_form': jugador_form,
        'rol': rol,
        'rol_choices': rol_choices,
        'equipos': equipos,
        'selected_equipo_id': selected_equipo_id,
    })


@login_required
def cambiar_password_obligatorio(request):
    """
    Vista para forzar el cambio de contraseña cuando un jugador 
    inicia sesión con la contraseña por defecto.
    """
    try:
        jugador = Jugador.objects.get(user=request.user)
    except Jugador.DoesNotExist:
        
        return redirect('usuario:home')
    
    
    if not jugador.tiene_password_por_defecto:
        return redirect('torneo:jugador')
    
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            
            jugador.tiene_password_por_defecto = False
            jugador.save()
            
            update_session_auth_hash(request, user)
            messages.success(request, _('Contraseña cambiada exitosamente.'))
            return redirect('torneo:jugador')
    else:
        form = PasswordChangeForm(user=request.user)
    
    return render(request, 'usuario/cambiar_password_obligatorio.html', {
        'form': form,
        'jugador': jugador
    })
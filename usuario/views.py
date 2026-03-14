from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import gettext as _
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from gestor.choices import RolUsuario, TipoUsuario
from torneo.models import Torneo
from .forms import UserRegisterForm, OrganizadorForm, EquipoForm, EmailAuthenticationForm, AdministradorForm, JugadorForm, UserUpdateForm
from .models import Organizador, Administrador, Jugador
from equipo.models import Equipo
from torneo.views import tipo_usuario


ROL_CHOICES = [
    RolUsuario.ORGANIZADOR,
    RolUsuario.EQUIPO,
]


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
    rol_form = RolForm(instance=rol_instance) if RolForm else None
    clave_form = PasswordChangeForm(user=usuario)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'datos':
            user_form = UserUpdateForm(request.POST, instance=usuario)
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
def borrar_usuario(request, usuario_id : int):
    pass

@login_required
def editar_usuario(request, usuario_id : int):
    return render(request, 'usuario/editar_usuario.html')

def crear_usuario(request):
    return render(request, 'usuario/crear_usuario.html')
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from gestor.choices import RolUsuario
from usuario.forms import UserRegisterForm, OrganizadorForm, EquipoForm, EmailAuthenticationForm
from usuario.models import Organizador, Administrador, Jugador
from equipo.models import Equipo


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
    return render(request, 'usuario/perfil.html')


@login_required
def admin_dashboard(request):
    return render(request, 'usuario/admin_dashboard.html')
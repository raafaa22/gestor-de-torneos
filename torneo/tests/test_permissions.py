import pytest

from torneo.views import tiene_permiso
from tests.utils import create_administrador, create_organizador, create_equipo, create_jugador, create_torneo, create_inscripcion_torneo


@pytest.mark.django_db
def test_tiene_permiso_devuelve_valor_esperado_por_rol():
    admin = create_administrador()
    organizador_creador = create_organizador(email="creador@test.com", nombre="Organizador Creador")
    equipo_inscrito = create_equipo(email="equipoinscrito@test.com", nombre="Equipo Inscrito")
    jugador_inscrito = create_jugador(equipo=equipo_inscrito)

    organizador_fuera = create_organizador(email="organizadorfuera@test.com", nombre="Organizador Fuera")
    equipo_fuera = create_equipo(email="equipofuera@test.com", nombre="Equipo Fuera")

    admin_user = admin.user
    usuario_organizador_creador = organizador_creador.user
    usuario_equipo_inscrito = equipo_inscrito.user
    usuario_jugador_inscrito = jugador_inscrito.user

    usuario_organizador_fuera = organizador_fuera.user
    usuario_equipo_fuera = equipo_fuera.user

    torneo = create_torneo(organizador=organizador_creador)
    create_inscripcion_torneo(torneo=torneo, equipo=equipo_inscrito)

    assert tiene_permiso(admin_user, torneo) is True
    assert tiene_permiso(usuario_organizador_creador, torneo) is True
    assert tiene_permiso(usuario_equipo_inscrito, torneo) is True
    assert tiene_permiso(usuario_jugador_inscrito, torneo) is True

    assert tiene_permiso(usuario_organizador_fuera, torneo) is False
    assert tiene_permiso(usuario_equipo_fuera, torneo) is False
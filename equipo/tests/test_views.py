import pytest
from django.urls import reverse

from tests.utils import create_equipo, create_jugador, create_organizador, create_torneo
from equipo.models import Equipo
from torneo.models import TorneoEquipo, Clasificacion
from estadisticas.models import EstadisticasFutbol
from usuario.models import Jugador


#Tests de integración para vistas de equipo


@pytest.mark.django_db
def test_crear_portero_desmarca_al_anterior(client):
    equipo = create_equipo(nombre="Equipo Porteros", email="equipo_porteros@test.com")
    usuario_equipo = equipo.user

    portero_antiguo = create_jugador(es_portero=True, equipo=equipo)

    client.force_login(usuario_equipo)

    response = client.post(
        reverse('equipo:crear_jugador', args=[equipo.id]),
        data={
            "email": "portero-nuevo@test.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
            "dni": "11111111A",
            "nombre": "Portero",
            "apellidos": "Nuevo",
            "es_portero": True,
        }
    )

    assert response.status_code == 302

    portero_antiguo.refresh_from_db()
    portero_nuevo=Jugador.objects.get(dni="11111111A")


    assert not portero_antiguo.es_portero
    assert portero_nuevo.es_portero
    assert portero_nuevo.equipo == equipo


@pytest.mark.django_db
def test_inscribir_equipo_liga_crea_clasificacion_y_estadisticas(client):
    equipo = create_equipo(nombre="Equipo Liga", email="equipo_liga@test.com")
    usuario_equipo = equipo.user

    create_jugador(equipo=equipo, email="jugliga1@test.com", dni="22222222B")
    create_jugador(equipo=equipo, email="jugliga2@test.com", dni="33333333C")

    organizador = create_organizador(email="organizador_liga@test.com", nombre="Organizador Liga")
    torneo = create_torneo(nombre="Torneo Liga", organizador=organizador)

    client.force_login(usuario_equipo)

    response = client.post(
        reverse('equipo:inscribirse', args=[equipo.id, torneo.id]),
    )

    assert response.status_code == 302
    assert TorneoEquipo.objects.filter(torneo=torneo, equipo=equipo).exists()

    te = TorneoEquipo.objects.get(torneo=torneo, equipo=equipo)
    assert Clasificacion.objects.filter(torneo_equipo=te).exists()
    assert EstadisticasFutbol.objects.filter(torneo=torneo, jugador__equipo=equipo).count() == 2


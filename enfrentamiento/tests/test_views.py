import pytest
from django.urls import reverse 

from tests.utils import create_organizador, create_torneo, create_equipo, create_inscripcion_torneo, create_enfrentamiento_liga
from torneo.models import Clasificacion


@pytest.mark.django_db
def test_guardar_enfrentamiento_liga_actualiza_resultado_y_clasificacion(client):
    organizador = create_organizador(email="orgresultado@test.com", nombre="Organizador Resultado")
    org_usuario = organizador.user

    torneo = create_torneo(nombre="Torneo Resultado", organizador=organizador)

    equipo_local = create_equipo(email="equipolocal@test.com", nombre="Equipo Local")
    equipo_visitante = create_equipo(email="equipovisitante@test.com", nombre="Equipo Visitante")

    te_local = create_inscripcion_torneo(torneo, equipo_local, posicion=1)
    te_visitante = create_inscripcion_torneo(torneo, equipo_visitante, posicion=2)

    enfrentamiento = create_enfrentamiento_liga(torneo=torneo, equipo_local=equipo_local, equipo_visitante=equipo_visitante, n_jornada=1)

    client.force_login(org_usuario)

    response = client.post(
        reverse("enfrentamientos:guardar_enfrentamiento", args=[torneo.id, 1, enfrentamiento.id]),
        data={
            "anotacion_local": 2,
            "anotacion_visitante": 1
        }
    )

    assert response.status_code == 302

    enfrentamiento.refresh_from_db()
    torneo.refresh_from_db()

    clasificacion_local = Clasificacion.objects.get(torneo_equipo=te_local)
    clasificacion_visitante = Clasificacion.objects.get(torneo_equipo=te_visitante)

    assert enfrentamiento.anotacion_local == 2
    assert enfrentamiento.anotacion_visitante == 1
    assert enfrentamiento.ganador == equipo_local

    assert clasificacion_local.puntos == 3
    assert clasificacion_local.victorias == 1
    assert clasificacion_local.empates == 0
    assert clasificacion_local.derrotas == 0
    assert clasificacion_local.anotacion_favor == 2
    assert clasificacion_local.anotacion_contra == 1

    assert clasificacion_visitante.puntos == 0
    assert clasificacion_visitante.victorias == 0
    assert clasificacion_visitante.empates == 0
    assert clasificacion_visitante.derrotas == 1
    assert clasificacion_visitante.anotacion_favor == 1
    assert clasificacion_visitante.anotacion_contra == 2

    assert torneo.ganador == equipo_local
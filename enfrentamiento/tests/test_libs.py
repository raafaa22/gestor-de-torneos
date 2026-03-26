import pytest

from tests.utils import create_varios_equipos, create_torneo, create_eliminatoria, create_enfrentamiento_eliminatoria
from enfrentamiento.libs import round_robin, actualizar_eliminatoria
from gestor.choices import TipoRonda, TipoTorneo


@pytest.mark.django_db
def test_round_robin_genera_rondas_correctas():
    equipos_pares = create_varios_equipos(8, prefijo="EquipoPar")
    jornadas_pares = round_robin(equipos_pares)

    assert len(jornadas_pares) == 7

    equipos_impares = create_varios_equipos(7, prefijo="EquipoImpar")
    jornadas_impares = round_robin(equipos_impares)

    assert len(jornadas_impares) == 7



@pytest.mark.django_db
def test_actualizar_eliminatoria_ganador_avanza_siguiente_ronda():
    torneo = create_torneo(tipo=TipoTorneo.ELIMINATORIA)
    equipos = create_varios_equipos(3, prefijo="EquipoElim")
    eliminatoria = create_eliminatoria(torneo, rondas=2)

    semifinal = create_enfrentamiento_eliminatoria(
        eliminatoria=eliminatoria,
        ronda=TipoRonda.SEMIFINAL,
        equipo_local=equipos[0],
        equipo_visitante=equipos[1]
    )

    final = create_enfrentamiento_eliminatoria(
        eliminatoria=eliminatoria,
        ronda=TipoRonda.FINAL,
        equipo_visitante=equipos[2],
        prev_local=semifinal,
    )

    semifinal.ganador = equipos[0]
    semifinal.save()

    actualizar_eliminatoria(semifinal)

    final.refresh_from_db()
    assert final.equipo_local == equipos[0]

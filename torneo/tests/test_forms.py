import pytest

from tests.utils import create_organizador
from torneo.forms import CrearTorneoForm
from gestor.choices import Deporte, TipoTorneo


@pytest.mark.django_db
def test_formulario_crear_torneo_necesita_n_equipos_playoffs_si_playoffs():
    organizador = create_organizador()

    usuario = organizador.user

    form = CrearTorneoForm(
        data={
            "nombre": "Liga con playoffs",
            "descripcion": "Torneo test",
            "max_equipos": 8,
            "deporte": Deporte.FUTBOL,
            "tipo": TipoTorneo.LIGA,
            "playoffs": True,
            "n_equipos_playoffs": "",
        },
        user=usuario
    )

    assert not form.is_valid()
    assert "n_equipos_playoffs" in form.errors


@pytest.mark.django_db
def test_formulario_crear_torneo_valida_n_grupos():
    organizador = create_organizador()
    usuario = organizador.user

    form = CrearTorneoForm(
        data={
            "nombre": "Torneo grupos inválido",
            "descripcion": "Torneo test",
            "max_equipos": 10,
            "deporte": Deporte.FUTBOL,
            "tipo": TipoTorneo.ELIMINATORIA_GRUPOS,
            "n_grupos": 3,
            "n_clasificados_grupo": 2,
        },
        user=usuario
    )

    assert not form.is_valid()
    assert "n_grupos" in form.errors
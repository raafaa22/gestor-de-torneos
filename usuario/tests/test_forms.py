import pytest

from tests.utils import CLAVE, create_user, create_equipo
from usuario.forms import UserRegisterForm, JugadorForm
from gestor.choices import Deporte

@pytest.mark.django_db
def test_formulario_registro_usuario_rechaza_email_existente():
    duplicado = "duplicado@test.com"
    create_user(email=duplicado)

    form = UserRegisterForm(
        data={
            "email": duplicado,
            "password1": CLAVE,
            "password2": CLAVE,
        }
    )

    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_formulario_jugador_esconde_es_portero_para_no_futbol():
    baloncesto = create_equipo(deporte=Deporte.BALONCESTO)
    padel = create_equipo(email="padel@test.com", nombre="Equipo Padel", deporte=Deporte.PADEL)

    form_baloncesto = JugadorForm(equipo=baloncesto)
    form_padel = JugadorForm(equipo=padel)

    assert "es_portero" not in form_baloncesto.fields
    assert "es_portero" not in form_padel.fields

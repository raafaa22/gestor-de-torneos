from .settings import *

# Más rápido en tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Opcional, pero útil para que el nombre sea explícito
DATABASES["default"]["TEST"] = {
    "NAME": "test_tfg",
}
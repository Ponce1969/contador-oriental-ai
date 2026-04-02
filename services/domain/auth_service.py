"""
Servicio de autenticación - Login, logout, gestión de usuarios
"""

import logging

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from result import Err, Ok, Result

from core.security import rate_limiter
from models.errors import DatabaseError, ValidationError
from models.user_model import User, UserCreate, UserLogin
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio de autenticación"""

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)

    def login(
        self, credentials: UserLogin
    ) -> Result[User, ValidationError | DatabaseError]:
        """
        Autenticar usuario con rate limiting.
        Retorna el usuario si las credenciales son correctas.
        """
        username = credentials.username

        # 1. Verificar si el usuario está bloqueado por demasiados fallos
        bloqueado, segundos = rate_limiter.esta_bloqueado(username)
        if bloqueado:
            minutos = segundos // 60 + 1
            return Err(
                ValidationError(
                    message=(
                        f"Demasiados intentos fallidos. "
                        f"Intentá de nuevo en {minutos} minuto(s)."
                    )
                )
            )

        # 2. Buscar usuario por username
        result = self._user_repo.get_by_username(username)
        if result.is_err():
            rate_limiter.registrar_fallo(username)
            return Err(ValidationError(message="Usuario o contraseña incorrectos"))

        user = result.ok_value

        # 3. Verificar que el usuario esté activo
        if not user.activo:
            return Err(ValidationError(message="Usuario inactivo"))

        # 4. Verificar contraseña
        if not self._verify_password(credentials.password, user.password_hash):
            bloqueado_ahora, seg_bloqueo = rate_limiter.registrar_fallo(username)
            if bloqueado_ahora:
                minutos = seg_bloqueo // 60 + 1
                return Err(
                    ValidationError(
                        message=(
                            f"Demasiados intentos fallidos. "
                            f"Cuenta bloqueada por {minutos} minuto(s)."
                        )
                    )
                )
            restantes = rate_limiter.intentos_restantes(username)
            return Err(
                ValidationError(
                    message=(
                        f"Usuario o contraseña incorrectos. "
                        f"Intentos restantes: {restantes}."
                    )
                )
            )

        # 5. Login exitoso — limpiar contador de fallos
        rate_limiter.registrar_exito(username)

        # 6. Actualizar último login
        if user.id is not None:
            self._user_repo.update_last_login(user.id)

        return Ok(user)

    def create_user(
        self, user_data: UserCreate
    ) -> Result[User, ValidationError | DatabaseError]:
        """Crear nuevo usuario con contraseña hasheada"""

        # Verificar que el username no exista
        existing = self._user_repo.get_by_username(user_data.username)
        if existing.is_ok():
            return Err(ValidationError(message="El nombre de usuario ya existe"))

        # Hashear contraseña
        password_hash = self._hash_password(user_data.password)

        # Crear usuario
        user = User(
            familia_id=user_data.familia_id,
            username=user_data.username,
            password_hash=password_hash,
            nombre_completo=user_data.nombre_completo,
            activo=True,
        )

        return self._user_repo.add(user)

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> Result[None, ValidationError | DatabaseError]:
        """Cambiar contraseña de usuario"""

        # Obtener usuario
        result = self._user_repo.get_by_id(user_id)
        if result.is_err():
            return Err(ValidationError(message="Usuario no encontrado"))

        user = result.ok_value

        # Verificar contraseña actual
        if not self._verify_password(old_password, user.password_hash):
            return Err(ValidationError(message="Contraseña actual incorrecta"))

        # Validar nueva contraseña
        if len(new_password) < 6:
            return Err(
                ValidationError(
                    message="La contraseña debe tener al menos 6 caracteres"
                )
            )

        # Hashear nueva contraseña
        new_hash = self._hash_password(new_password)

        # Actualizar
        return self._user_repo.update_password(user_id, new_hash)

    def _hash_password(self, password: str) -> str:
        """Hashear contraseña con Argon2"""
        return self._ph.hash(password)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verificar contraseña contra hash con Argon2"""
        try:
            self._ph.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            return False

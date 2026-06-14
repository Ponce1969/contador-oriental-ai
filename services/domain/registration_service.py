"""
Servicio de registro de familias y usuarios
"""

from __future__ import annotations

import logging

from argon2 import PasswordHasher
from result import Err, Ok, Result
from sqlalchemy import text

from core.unit_of_work import UnitOfWork
from models.user_model import User

logger = logging.getLogger(__name__)


class RegistrationService:
    """Servicio para registrar nuevas familias y usuarios"""

    def __init__(self, uow: UnitOfWork | None = None) -> None:
        self._ph = PasswordHasher()
        self._uow = uow

    def register_family(
        self,
        familia_nombre: str,
        familia_email: str,
        admin_username: str,
        admin_password: str,
        admin_nombre_completo: str,
    ) -> Result[User, str]:
        """
        Registra una nueva familia con su primer usuario admin

        Args:
            familia_nombre: Nombre de la familia
            familia_email: Email de contacto de la familia
            admin_username: Username del primer usuario admin
            admin_password: Contraseña del admin
            admin_nombre_completo: Nombre completo del admin

        Returns:
            Result con el Usuario creado o mensaje de error
        """
        validation_error = self._validate_registration_data(
            familia_nombre, familia_email, admin_username, admin_password
        )
        if validation_error:
            return Err(validation_error)

        if self._uow is not None:
            return self._register_with_uow(
                familia_nombre,
                familia_email,
                admin_username,
                admin_password,
                admin_nombre_completo,
            )

        with UnitOfWork() as uow:
            return self._do_registration(
                uow,
                familia_nombre,
                familia_email,
                admin_username,
                admin_password,
                admin_nombre_completo,
            )

    def _register_with_uow(
        self,
        familia_nombre: str,
        familia_email: str,
        admin_username: str,
        admin_password: str,
        admin_nombre_completo: str,
    ) -> Result[User, str]:
        with self._uow as uow:
            return self._do_registration(
                uow,
                familia_nombre,
                familia_email,
                admin_username,
                admin_password,
                admin_nombre_completo,
            )

    def _do_registration(
        self,
        uow: UnitOfWork,
        familia_nombre: str,
        familia_email: str,
        admin_username: str,
        admin_password: str,
        admin_nombre_completo: str,
    ) -> Result[User, str]:
        session = uow.session

        email_exists = session.execute(
            text("SELECT id FROM familias WHERE email = :email"),
            {"email": familia_email},
        ).fetchone()

        if email_exists:
            return Err("El email de familia ya está registrado")

        username_exists = session.execute(
            text("SELECT id FROM usuarios WHERE username = :username"),
            {"username": admin_username},
        ).fetchone()

        if username_exists:
            return Err("El nombre de usuario ya está en uso")

        result = session.execute(
            text("""
                INSERT INTO familias (nombre, email, activo, created_at)
                VALUES (:nombre, :email, TRUE, CURRENT_TIMESTAMP)
                RETURNING id
            """),
            {"nombre": familia_nombre, "email": familia_email},
        )
        familia_id = result.fetchone()[0]

        password_hash = self._ph.hash(admin_password)

        result = session.execute(
            text("""
                INSERT INTO usuarios (
                    familia_id, username, password_hash,
                    nombre_completo, email, activo, created_at
                )
                VALUES (
                    :familia_id, :username, :password_hash,
                    :nombre_completo, :email, TRUE, CURRENT_TIMESTAMP
                )
                RETURNING id
            """),
            {
                "familia_id": familia_id,
                "username": admin_username,
                "password_hash": password_hash,
                "nombre_completo": admin_nombre_completo,
                "email": familia_email,
            },
        )
        usuario_id = result.fetchone()[0]

        uow.flush()

        return Ok(
            User(
                id=usuario_id,
                familia_id=familia_id,
                username=admin_username,
                password_hash=password_hash,
                nombre_completo=admin_nombre_completo,
                email=familia_email,
                activo=True,
            )
        )

    def _validate_registration_data(
        self, familia_nombre: str, familia_email: str, username: str, password: str
    ) -> str | None:
        """
        Valida los datos de registro

        Returns:
            Mensaje de error o None si todo está bien
        """
        if not familia_nombre or len(familia_nombre.strip()) < 3:
            return "El nombre de familia debe tener al menos 3 caracteres"

        if not familia_email or "@" not in familia_email:
            return "Email de familia inválido"

        if not username or len(username.strip()) < 3:
            return "El nombre de usuario debe tener al menos 3 caracteres"

        if not password or len(password) < 6:
            return "La contraseña debe tener al menos 6 caracteres"

        return None

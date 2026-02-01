"""
Repositorio de usuarios - Acceso a datos de autenticación
"""
from result import Err, Ok, Result
from sqlalchemy import text

from core.sqlalchemy_session import get_db_session
from models.errors import DatabaseError
from models.user_model import User


class UserRepository:
    """Repositorio para gestión de usuarios"""
    
    def __init__(self, session=None):
        self._session = session
    
    def _get_session(self):
        """Get session - use provided or global"""
        if self._session is not None:
            return self._session
        # Return the context manager, not the session directly
        return get_db_session()

    def _use_session(self, callback):
        """Execute callback with appropriate session handling"""
        if self._session is not None:
            # Use injected session (test mode) - already in context
            return callback(self._session)
        else:
            # Use global session (production mode) - manage context
            with get_db_session() as session:
                return callback(session)

    def get_by_username(self, username: str) -> Result[User, DatabaseError]:
        """Obtener usuario por nombre de usuario"""
        def _query(session):
            result = session.execute(
                text("""
                    SELECT 
                        id, familia_id, username, password_hash,
                        nombre_completo, activo, created_at, last_login
                    FROM usuarios
                    WHERE username = :username
                """),
                {"username": username}
            )
            row = result.fetchone()

            if not row:
                return Err(
                    DatabaseError(message=f"Usuario {username} no encontrado")
                )

            user = User(
                id=row[0],
                familia_id=row[1],
                username=row[2],
                password_hash=row[3],
                nombre_completo=row[4],
                activo=row[5],
                created_at=row[6],
                last_login=row[7],
            )
            return Ok(user)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al buscar usuario: {e}"))
                
    def get_by_id(self, user_id: int) -> Result[User, DatabaseError]:
        """Obtener usuario por ID"""
        def _query(session):
            result = session.execute(
                text("""
                    SELECT
                        id, familia_id, username, password_hash,
                        nombre_completo, activo, created_at, last_login
                    FROM usuarios
                    WHERE id = :user_id
                """),
                {"user_id": user_id}
            )
            row = result.fetchone()

            if not row:
                return Err(
                    DatabaseError(message=f"Usuario con ID {user_id} no encontrado")
                )

            user = User(
                id=row[0],
                familia_id=row[1],
                username=row[2],
                password_hash=row[3],
                nombre_completo=row[4],
                activo=bool(row[5]),
                created_at=row[6],
                last_login=row[7]
            )
            return Ok(user)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al buscar usuario: {str(e)}"))
    
    def add(self, user: User) -> Result[User, DatabaseError]:
        """Crear nuevo usuario"""
        def _query(session):
            result = session.execute(
                text("""
                    INSERT INTO usuarios (
                        familia_id, username, password_hash,
                        nombre_completo, activo
                    )
                    VALUES (
                        :familia_id, :username, :password_hash,
                        :nombre_completo, :activo
                    )
                    RETURNING id, created_at
                """),
                {
                    "familia_id": user.familia_id,
                    "username": user.username,
                    "password_hash": user.password_hash,
                    "nombre_completo": user.nombre_completo,
                    "activo": user.activo
                }
            )
            row = result.fetchone()

            if row is not None:
                user.id = row[0]
                user.created_at = row[1]

            return Ok(user)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(DatabaseError(message=f"Error al crear usuario: {str(e)}"))
    
    def update_last_login(self, user_id: int) -> Result[None, DatabaseError]:
        """Actualizar fecha de último login"""
        def _query(session):
            session.execute(
                text("""
                    UPDATE usuarios
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """),
                {"user_id": user_id}
            )
            return Ok(None)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(
                DatabaseError(message=f"Error al actualizar último login: {str(e)}")
            )
    
    def update_password(
        self, user_id: int, new_password_hash: str
    ) -> Result[None, DatabaseError]:
        """Actualizar contraseña de usuario"""
        def _query(session):
            session.execute(
                text("""
                    UPDATE usuarios
                    SET password_hash = :password_hash
                    WHERE id = :user_id
                """),
                {"user_id": user_id, "password_hash": new_password_hash}
            )
            return Ok(None)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(
                DatabaseError(message=f"Error al actualizar contraseña: {str(e)}")
            )
    
    def get_by_familia(self, familia_id: int) -> Result[list[User], DatabaseError]:
        """Obtener todos los usuarios de una familia"""
        def _query(session):
            result = session.execute(
                text("""
                    SELECT
                        id, familia_id, username, password_hash,
                        nombre_completo, activo, created_at, last_login
                    FROM usuarios
                    WHERE familia_id = :familia_id
                    ORDER BY username
                """),
                {"familia_id": familia_id}
            )

            users = []
            for row in result:
                user = User(
                    id=row[0],
                    familia_id=row[1],
                    username=row[2],
                    password_hash=row[3],
                    nombre_completo=row[4],
                    activo=bool(row[5]),
                    created_at=row[6],
                    last_login=row[7]
                )
                users.append(user)

            return Ok(users)

        try:
            return self._use_session(_query)
        except Exception as e:
            return Err(
                DatabaseError(message=f"Error al listar usuarios: {str(e)}")
            )

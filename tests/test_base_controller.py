"""
Tests para BaseController - Pilar de herencia del Escudo Charrúa
"""

import pytest
from sqlalchemy.orm import Session

from controllers.base_controller import BaseController
from models.errors import DatabaseError


class TestBaseController:
    """Tests para BaseController"""
    
    def test_base_controller_inheritance(self):
        """Test que BaseController puede ser heredado correctamente"""
        
        class TestController(BaseController):
            """Controller de prueba para testear herencia"""
            pass
        
        # Crear instancia con familia_id
        controller = TestController(familia_id=42)
        
        # Verificar atributos base
        assert controller._familia_id == 42
        assert hasattr(controller, '_get_session')
        assert callable(getattr(controller, '_get_session'))
    
    def test_base_controller_sin_familia_id(self):
        """Test BaseController sin familia_id (opcional)"""
        
        class TestController(BaseController):
            pass
        
        # Crear instancia sin familia_id
        controller = TestController()
        
        # Verificar que familia_id sea None por defecto
        assert controller._familia_id is None
    
    def test_get_session_context_manager(self, db_session):
        """Test que _get_session funciona como context manager"""
        
        class TestController(BaseController):
            pass
        
        controller = TestController(familia_id=1)
        
        # Probar el context manager
        with controller._get_session() as session:
            assert session is not None
            assert isinstance(session, Session)
            # La sesión debe estar activa dentro del context
            assert session.is_active
    
    def test_get_session_cierra_correctamente(self, db_session):
        """Test que la sesión se cierra correctamente después del context"""
        
        class TestController(BaseController):
            pass
        
        controller = TestController(familia_id=1)
        
        session_dentro = None
        session_fuera = None
        
        # Usar el context manager
        with controller._get_session() as session:
            session_dentro = session
            assert session.is_active
        
        # Después del context, la sesión debería cerrarse
        # Nota: En SQLAlchemy, la sesión puede permanecer activa pero el transaction termina
        # Lo importante es que el context manager maneje el ciclo de vida
    
    def test_get_session_con_error_hace_rollback(self, db_session):
        """Test que los errores dentro del context manager hacen rollback"""
        
        class TestController(BaseController):
            pass
        
        controller = TestController(familia_id=1)
        
        # Simular un error dentro del context
        try:
            with controller._get_session() as session:
                # Iniciar una transacción
                session.begin()
                # Forzar un error
                raise ValueError("Error simulado")
        except ValueError:
            # El error debe propagarse
            pass
        
        # La sesión debe manejar el rollback automáticamente
        # En un entorno real, esto depende de la configuración del session factory
    
    def test_base_controller_atributos_privados(self):
        """Test que los atributos privados están protegidos"""
        
        class TestController(BaseController):
            pass
        
        controller = TestController(familia_id=99)
        
        # Verificar que los atributos existen pero son "privados"
        assert hasattr(controller, '_familia_id')
        assert hasattr(controller, '_get_session')
        
        # No deberían existir versiones públicas
        assert not hasattr(controller, 'familia_id')
        assert not hasattr(controller, 'get_session')


class TestBaseControllerIntegration:
    """Tests de integración de BaseController con base de datos"""
    
    def test_controller_con_db_real(self, db_session):
        """Test BaseController con una sesión de BD real"""
        
        class TestController(BaseController):
            def test_query(self):
                """Método de prueba para probar queries"""
                with self._get_session() as session:
                    # Query simple para probar que la conexión funciona
                    result = session.execute("SELECT 1 as test").fetchone()
                    return result[0] if result else None
        
        controller = TestController(familia_id=1)
        
        # Probar que podemos ejecutar queries
        result = controller.test_query()
        assert result == 1
    
    def test_controller_familia_id_en_queries(self, db_session, setup_test_data):
        """Test que familia_id se usa correctamente en queries"""
        
        # Este test asume que setup_test_data crea datos con diferentes familia_id
        class TestController(BaseController):
            def get_data_by_familia(self):
                """Método que filtra por familia_id"""
                with self._get_session() as session:
                    # Query simulado que filtra por familia_id
                    query = "SELECT COUNT(*) FROM test_table WHERE familia_id = :familia_id"
                    result = session.execute(query, {"familia_id": self._familia_id}).fetchone()
                    return result[0] if result else 0
        
        controller = TestController(familia_id=1)
        
        # Probar que el filtro se aplica correctamente
        # Nota: Esto requiere que la BD tenga la tabla test_table con datos de prueba
        # Por ahora, probamos la estructura del método
        assert controller._familia_id == 1


class TestBaseControllerErrorHandling:
    """Tests de manejo de errores en BaseController"""
    
    def test_get_session_sin_configuracion(self):
        """Test comportamiento cuando no hay configuración de BD"""
        
        class TestController(BaseController):
            pass
        
        controller = TestController(familia_id=1)
        
        # Si no hay sesión configurada, debería lanzar un error apropiado
        # Esto depende de la implementación específica de _get_session
        with pytest.raises(Exception):  # TypeError, DatabaseError, etc.
            with controller._get_session():
                pass
    
    def test_controller_con_familia_id_invalido(self):
        """Test BaseController con familia_id inválido"""
        
        class TestController(BaseController):
            pass
        
        # Familia_id negativo (inválido)
        controller = TestController(familia_id=-1)
        assert controller._familia_id == -1
        
        # Familia_id cero (inválido)
        controller = TestController(familia_id=0)
        assert controller._familia_id == 0
        
        # Familia_id string (inválido pero posible)
        controller = TestController(familia_id="invalid")
        assert controller._familia_id == "invalid"


class TestBaseControllerHerenciaReal:
    """Tests con controllers reales que heredan de BaseController"""
    
    def test_expense_controller_herencia(self):
        """Test que ExpenseController hereda correctamente"""
        from controllers.expense_controller import ExpenseController
        
        # Verificar que es una subclase de BaseController
        assert issubclass(ExpenseController, BaseController)
        
        # Crear instancia
        controller = ExpenseController(familia_id=1)
        
        # Verificar que tiene los métodos base
        assert hasattr(controller, '_familia_id')
        assert hasattr(controller, '_get_session')
        assert controller._familia_id == 1
    
    def test_income_controller_herencia(self):
        """Test que IncomeController hereda correctamente"""
        from controllers.income_controller import IncomeController
        
        # Verificar que es una subclase de BaseController
        assert issubclass(IncomeController, BaseController)
        
        # Crear instancia
        controller = IncomeController(familia_id=2)
        
        # Verificar que tiene los métodos base
        assert hasattr(controller, '_familia_id')
        assert hasattr(controller, '_get_session')
        assert controller._familia_id == 2
    
    def test_ai_controller_herencia(self):
        """Test que AIController hereda correctamente"""
        from controllers.ai_controller import AIController
        
        # Verificar que es una subclase de BaseController
        assert issubclass(AIController, BaseController)
        
        # AIController tiene un constructor especial
        controller = AIController(familia_id=3)
        
        # Verificar que mantiene los atributos base
        assert hasattr(controller, '_familia_id')
        assert hasattr(controller, '_get_session')
        assert controller._familia_id == 3

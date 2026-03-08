

import sqlite3
from pathlib import Path

# import mysql.connector
from configs.database import DATABASE

BASE_DIR = Path(__file__).resolve().parent.parent
_connection = None

def get_connection():
    global _connection

    if _connection is not None:
        return _connection

    engine = DATABASE.get("ENGINE", "sqlite").lower()

    if engine == "sqlite":
        _connection = _connect_sqlite()
    elif engine == "mysql":
        _connection = _connect_mysql()
    elif engine == "postgresql":
        _connection = _connect_postgresql()
    else:
        raise RuntimeError(f"Unsupported database engine: {engine}")

    return _connection

# =========================
# SQLITE
# =========================
def _connect_sqlite():
    cfg = DATABASE.get("SQLITE", {})
    path_cfg = cfg.get("PATH", "data/fleting.db") if isinstance(cfg, dict) else "data/fleting.db"

    db_path = BASE_DIR / Path(str(path_cfg))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return sqlite3.connect(db_path)

# =========================
# POSTGRESQL
# =========================
class _PostgreSQLConnectionAdapter:
    """
    Adapta psycopg2 para que tenga la misma API que sqlite3:
    conn.execute(sql, params) y conn.commit().
    Necesario para compatibilidad con el CLI de Fleting.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        from sqlalchemy.sql.elements import TextClause
        if isinstance(sql, TextClause):
            sql = str(sql)
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _connect_postgresql():
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError(
            "PostgreSQL support requires `psycopg2`: "
            "uv add psycopg2-binary"
        )

    cfg = DATABASE.get("POSTGRESQL", {})
    conn = psycopg2.connect(
        host=cfg.get("HOST", "localhost"),
        port=cfg.get("PORT", 5432),
        user=cfg.get("USER"),
        password=cfg.get("PASSWORD"),
        dbname=cfg.get("NAME"),
    )
    conn.autocommit = False
    return _PostgreSQLConnectionAdapter(conn)


# =========================
# MYSQL
# =========================
def _connect_mysql():
    pass
    # try:
    #     import mysql.connector
    # except ImportError:
    #     raise RuntimeError(
    #         "MySQL support requires `mysql-connector-python` :"
    #         "pip install mysql-connector-python"
    #     )

    # cfg = DATABASE.get("MYSQL", {})

    # return mysql.connector.connect(
    #     host=cfg.get("HOST", "localhost"),
    #     port=cfg.get("PORT", 3306),
    #     user=cfg.get("USER"),
    #     password=cfg.get("PASSWORD"),
    #     database=cfg.get("NAME"),
    #     charset=cfg.get("OPTIONS", {}).get("charset", "utf8mb4"),
    # )


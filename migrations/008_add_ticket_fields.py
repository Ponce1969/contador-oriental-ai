"""
Migration: agregar campos OCR a la tabla expenses.
Permite registrar el origen del gasto (ticket fotográfico) y auditar
la calidad del reconocimiento óptico de caracteres.
"""


def up(conn):
    conn.execute("""
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS ticket_image_path TEXT
    """)
    conn.execute("""
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS ocr_texto_crudo TEXT
    """)
    conn.execute("""
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS ocr_confianza FLOAT
    """)


def down(conn):
    conn.execute("""
        ALTER TABLE expenses
        DROP COLUMN IF EXISTS ticket_image_path,
        DROP COLUMN IF EXISTS ocr_texto_crudo,
        DROP COLUMN IF EXISTS ocr_confianza
    """)

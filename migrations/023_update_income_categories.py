"""
Migration: update_income_categories
Created at: 2026-09-05T00:35:00.000000
"""


def up(db):
    db.execute("""
        UPDATE incomes
        SET categoria = '🛠️ Independiente / Unipersonal'
        WHERE categoria LIKE '%Freelance%'
    """)
    db.execute("""
        UPDATE incomes
        SET categoria = '👴 Jubilación / Pensión'
        WHERE categoria LIKE '%Jubilad%'
    """)


def down(db):
    db.execute("""
        UPDATE incomes
        SET categoria = '💻 Freelance'
        WHERE categoria LIKE '%Independiente%'
    """)
    db.execute("""
        UPDATE incomes
        SET categoria = '👴 Jubilado/a'
        WHERE categoria LIKE '%Jubilación%'
    """)

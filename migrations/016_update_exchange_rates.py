"""
Migration: update_exchange_rates
Created at: 2026-07-31T20:25:00
Updates exchange rate tracking table for USD/UYU to support compra and venta.
"""


def up(db):
    db.execute("ALTER TABLE exchange_rates ADD COLUMN compra NUMERIC(10, 4) DEFAULT 0 NOT NULL")
    db.execute("ALTER TABLE exchange_rates ADD COLUMN venta NUMERIC(10, 4) DEFAULT 0 NOT NULL")
    
    db.execute("UPDATE exchange_rates SET compra = rate, venta = rate")
    
    db.execute("ALTER TABLE exchange_rates DROP COLUMN rate")


def down(db):
    db.execute("ALTER TABLE exchange_rates ADD COLUMN rate NUMERIC(10, 4) DEFAULT 0 NOT NULL")
    db.execute("UPDATE exchange_rates SET rate = compra")
    db.execute("ALTER TABLE exchange_rates DROP COLUMN compra")
    db.execute("ALTER TABLE exchange_rates DROP COLUMN venta")

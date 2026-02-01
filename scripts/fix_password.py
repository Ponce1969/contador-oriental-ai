"""Fix admin password"""
import argon2
from database.engine import engine
from sqlalchemy import text

ph = argon2.PasswordHasher()

with engine.connect() as conn:
    result = conn.execute(text('SELECT password_hash FROM usuarios WHERE username = "admin"'))
    row = result.fetchone()
    if row:
        stored_hash = row[0]
        print(f'Hash stored: {stored_hash[:60]}...')
        try:
            ph.verify(stored_hash, 'admin123')
            print('✅ Password admin123 is CORRECT')
        except argon2.exceptions.VerifyMismatchError:
            print('❌ Password admin123 is INCORRECT')
            print('Generating new hash for admin123...')
            new_hash = ph.hash('admin123')
            conn.execute(text('UPDATE usuarios SET password_hash = :h WHERE username = "admin"'), {'h': new_hash})
            conn.commit()
            print('✅ Password reset. Try logging in now.')

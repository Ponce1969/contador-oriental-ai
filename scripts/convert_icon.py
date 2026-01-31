"""
Script para convertir icon-gastos.png a formato .ico para Windows
"""
from PIL import Image

# Abrir la imagen PNG
img = Image.open("assets/icon-gastos.png")

# Convertir a formato ICO con múltiples tamaños
img.save(
    "assets/icon-gastos.ico",
    format='ICO',
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)

print("✅ Icono convertido exitosamente a icon-gastos.ico")

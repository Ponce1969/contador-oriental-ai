#!/usr/bin/env python3
"""
Auditor Real — Solo detecta problemas reales de deuda técnica
Ignora falsos positivos de imports no usados
"""

import ast
import re
from pathlib import Path


class AuditorReal:
    def __init__(self, root_path="."):
        self.root = Path(root_path)
        self.issues = {"CRÍTICO": [], "ALTO": [], "MEDIO": []}

    def log(self, level, msg, file, line=None):
        loc = f"{file}:{line}" if line else file
        self.issues[level].append(f"[{level}] {loc} -> {msg}")

    def analizar_controllers(self):
        """Verifica que no haya duplicación de _get_session"""
        controllers_dir = self.root / "controllers"
        if not controllers_dir.exists():
            return

        for file in controllers_dir.glob("*.py"):
            if file.name.startswith("base_") or file.name == "__init__.py":
                continue

            try:
                with open(file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    
                    # Buscar _get_session duplicado
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name == "_get_session":
                            self.log("CRÍTICO", "Context manager duplicado. Usar BaseController.", file.name, node.lineno)
            except:
                continue

    def analizar_strings_magicos(self):
        """Detecta strings repetidos que deberían ser constantes"""
        strings_vistos = {}
        
        for file in self.root.rglob("*.py"):
            if "venv" in str(file) or ".history" in str(file) or "__pycache__" in str(file):
                continue
                
            try:
                with open(file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Constant) and isinstance(node.value, str):
                            # Solo strings que parecen mensajes de error o validación
                            string = node.value
                            if 10 <= len(string) <= 60 and any(char in string for char in "áéíóúñ"):
                                if string not in strings_vistos:
                                    strings_vistos[string] = []
                                strings_vistos[string].append((file.name, node.lineno))
            except:
                continue
        
        # Reportar strings repetidos
        for string, locations in strings_vistos.items():
            if len(locations) > 1:
                files = ", ".join(f"{loc[0]}" for loc in locations)
                self.log("MEDIO", f"String repetido {len(locations)} veces: '{string[:30]}...' en {files}", "global")

    def analizar_formateo_manual(self):
        """Detecta formateo de moneda manual"""
        pattern = re.compile(r":,\.0f")
        for file in self.root.glob("views/pages/*.py"):
            try:
                with open(file, encoding="utf-8") as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        if pattern.search(line):
                            self.log("MEDIO", "Formateo de moneda manual. Usar helper centralizado.", file.name, i)
            except:
                continue

    def analizar_try_except_vacios(self):
        """Detecta except: pass peligrosos"""
        for file in self.root.rglob("*.py"):
            if "venv" in str(file) or ".history" in str(file) or "__pycache__" in str(file):
                continue
                
            try:
                with open(file, encoding="utf-8") as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        if re.search(r"except:\s*pass", line) or re.search(r"except Exception:\s*pass", line):
                            self.log("ALTO", "Antipatrón 'except: pass' detectado. Oculta errores.", file.name, i)
            except:
                continue

    def ejecutar(self):
        print("=" * 70)
        print("AUDITOR REAL - SOLO PROBLEMAS REALES")
        print("=" * 70)
        
        self.analizar_controllers()
        self.analizar_strings_magicos()
        self.analizar_formateo_manual()
        self.analizar_try_except_vacios()
        
        # Reporte
        total = 0
        for level in ["CRÍTICO", "ALTO", "MEDIO"]:
            count = len(self.issues[level])
            total += count
            
            if count > 0:
                print(f"\n{level} ({count} problemas):")
                for issue in self.issues[level]:
                    print(f"   - {issue}")
        
        if total == 0:
            print("\n✅ PROYECTO LIMPIO - Sin deuda técnica detectada")
        else:
            print(f"\n⚠️ Total de problemas reales: {total}")
            
            if self.issues["CRÍTICO"]:
                print("🔥 PROBLEMAS CRÍTICOS - Revisar antes de deploy")
            elif self.issues["ALTO"]:
                print("⚡ PROBLEMAS DE ALTA PRIORIDAD - Recomendado revisar")
            else:
                print("📝 PROBLEMAS MENORES - Se pueden abordar luego")


if __name__ == "__main__":
    AuditorReal().ejecutar()

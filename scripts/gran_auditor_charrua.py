#!/usr/bin/env python3
"""
Gran Auditor Charrúa — Escáner integral de deuda técnica
Detecta patrones de código problemáticos en el proyecto Contador Oriental
"""

import ast
import re
from collections import Counter
from pathlib import Path


class GranAuditorCharrua:
    def __init__(self, root_path="."):
        self.root = Path(root_path)
        self.issues = {"CRÍTICO": [], "ALTO": [], "MEDIO": []}
        self.stats = {
            "archivos_analizados": 0,
            "lineas_totales": 0,
            "clases_encontradas": 0,
            "metodos_encontrados": 0,
        }

    def log(self, level: str, msg: str, file: str, line: int | None = None) -> None:
        loc = f"{file}:{line}" if line else file
        self.issues[level].append(f"[{level}] {loc} -> {msg}")

    def contar_lineas(self, file_path: Path) -> int:
        """Cuenta líneas de código reales (ignorando vacías y comentarios)."""
        try:
            with open(file_path, encoding="utf-8") as f:
                return sum(
                    1 for line in f
                    if line.strip() and not line.strip().startswith("#")
                )
        except:
            return 0

    def analizar_herencia_y_sesion(self, folder: str, base_class: str, suffix: str) -> None:
        """Verifica que controllers y repos hereden de sus bases y no dupliquen lógica."""
        path = self.root / folder
        if not path.exists():
            return

        for file in path.glob("*.py"):
            if file.name.startswith("base_") or file.name == "__init__.py":
                continue

            self.stats["archivos_analizados"] += 1
            self.stats["lineas_totales"] += self.contar_lineas(file)

            try:
                with open(file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            self.stats["clases_encontradas"] += 1
                            
                            # Verificar Herencia
                            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                            if base_class not in bases:
                                self.log("CRÍTICO", f"No hereda de {base_class}", file.name)
                            
                        elif isinstance(node, ast.FunctionDef):
                            self.stats["metodos_encontrados"] += 1
                            
                            # Verificar duplicación de métodos que deben estar en la base
                            if node.name in ["_get_session", "get_db"]:
                                self.log("CRÍTICO", f"Re-implementa {node.name}. Usar herencia.", file.name, node.lineno)
                            
                            # Detectar context managers duplicados
                            if node.name == "_get_session":
                                self.log("CRÍTICO", "Context manager duplicado. Mover a BaseController.", file.name, node.lineno)
                                
            except SyntaxError as e:
                self.log("CRÍTICO", f"Error de sintaxis: {e}", file.name)

    def analizar_repositories_duplicados(self) -> None:
        """Busca métodos CRUD repetidos que podrían ir en un BaseRepository."""
        repo_dir = self.root / "repositories"
        if not repo_dir.exists():
            return
        
        metodos_encontrados = []
        for file in repo_dir.glob("*.py"):
            if "base" in file.name:
                continue
                
            try:
                with open(file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            metodos_encontrados.append(node.name)
            except:
                continue
        
        # Si un método se repite mucho, sugerir abstracción
        counts = Counter(metodos_encontrados)
        for metodo, count in counts.items():
            if count > 2 and metodo not in ["__init__"]:
                self.log("ALTO", f"Método '{metodo}' repetido en {count} repositorios. ¿Crear BaseRepository?", "repositories/")

    def analizar_bloques_try_except_vacios(self) -> None:
        """Detecta el antipatrón 'except: pass' que oculta errores en producción."""
        for file in self.root.rglob("*.py"):
            if "venv" in str(file) or ".history" in str(file) or "__pycache__" in str(file):
                continue
                
            try:
                with open(file, encoding="utf-8") as f:
                    content = f.read()
                    
                    # Buscamos la combinación peligrosa
                    if re.search(r"except:\s+pass", content):
                        self.log("ALTO", "Antipatrón 'except: pass' detectado. Esto oculta bugs.", file.name)
                    elif re.search(r"except Exception:\s+pass", content):
                        self.log("ALTO", "Antipatrón 'except Exception: pass' detectado. Esto oculta bugs.", file.name)
            except:
                continue

    def analizar_hardcoded_formatting(self) -> None:
        """Busca formateo de moneda/números manual en lugar de usar una constante/función."""
        pattern = re.compile(r":,\.0f")
        for file in self.root.glob("views/pages/*.py"):
            try:
                with open(file, encoding="utf-8") as f:
                    if pattern.search(f.read()):
                        self.log("MEDIO", "Formateo de moneda manual detectado. Usar constant o helper.", file.name)
            except:
                continue

    def analizar_strings_magicos(self) -> None:
        """Detecta strings literales repetidos que deberían ser constantes."""
        strings_encontrados = Counter()
        
        for file in self.root.rglob("*.py"):
            if "venv" in str(file) or ".history" in str(file) or "__pycache__" in str(file):
                continue
                
            try:
                with open(file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Constant) and isinstance(node.value, str):
                            # Ignorar strings muy cortos o muy largos
                            if 10 <= len(node.value) <= 50 and node.value.strip():
                                strings_encontrados[node.value] += 1
            except:
                continue
        
        # Reportar strings repetidos
        for string, count in strings_encontrados.most_common(10):
            if count > 2:
                self.log("MEDIO", f"String repetido {count} veces: '{string[:30]}...'. ¿Crear constante?", "global")

    def analizar_imports_no_usados(self) -> None:
        """Detecta imports que no se utilizan en el archivo."""
        for file in self.root.glob("**/*.py"):
            if "venv" in str(file) or ".history" in str(file) or "__pycache__" in str(file):
                continue
                
            try:
                with open(file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                    
                    # Recolectar imports
                    imports = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                    
                    # Recolectar nombres usados
                    usados = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name):
                            usados.add(node.id)
                    
                    # Detectar imports no usados
                    no_usados = imports - usados
                    for imp in no_usados:
                        if imp not in ["os", "sys", "typing"]:  # Comunes que pueden ser usados indirectamente
                            self.log("MEDIO", f"Import no utilizado: {imp}", file.name)
            except:
                continue

    def ejecutar(self) -> None:
        print(f"{'='*70}")
        print("AUDITORIA INTEGRAL: PROYECTO CONTADOR ORIENTAL")
        print(f"{'='*70}")
        
        # Ejecutar todos los análisis
        print("Analizando controllers y repositories...")
        self.analizar_herencia_y_sesion("controllers", "BaseController", "controller")
        self.analizar_herencia_y_sesion("repositories", "BaseRepository", "repository")
        self.analizar_repositories_duplicados()
        
        print("Analizando calidad de codigo...")
        self.analizar_bloques_try_except_vacios()
        self.analizar_hardcoded_formatting()
        self.analizar_strings_magicos()
        self.analizar_imports_no_usados()
        
        # Estadísticas
        print("\nESTADISTICAS DEL PROYECTO:")
        print(f"   Archivos analizados: {self.stats['archivos_analizados']}")
        print(f"   Lineas de codigo: {self.stats['lineas_totales']}")
        print(f"   Clases encontradas: {self.stats['clases_encontradas']}")
        print(f"   Metodos encontrados: {self.stats['metodos_encontrados']}")
        
        # Reporte Final
        total_problemas = 0
        for level in ["CRÍTICO", "ALTO", "MEDIO"]:
            count = len(self.issues[level])
            total_problemas += count
            
            if count > 0:
                print(f"\n{level} ({count} problemas):")
                for issue in self.issues[level]:
                    print(f"   - {issue}")
        
        if total_problemas == 0:
            print("\nPROYECTO LIMPIO: Tu codigo esta optimizado y listo para produccion.")
        else:
            print(f"\nTotal de problemas encontrados: {total_problemas}")
            
            if self.issues["CRÍTICO"]:
                print("HAY PROBLEMAS CRITICOS - Revisar antes de hacer deploy")
            elif self.issues["ALTO"]:
                print("Hay problemas de prioridad ALTA - Recomendado revisar")
            else:
                print("Problemas menores - Se pueden abordar en el proximo sprint")


if __name__ == "__main__":
    # Asegúrate de ejecutarlo en la raíz del proyecto
    auditor = GranAuditorCharrua()
    auditor.ejecutar()

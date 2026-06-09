"""
Auditor de arquitectura: detecta uso directo de repositorios en controllers.

Este script identifica patrones problemáticos donde los controllers usan
directamente los repositorios en lugar de los servicios de dominio.

Problema detectado:
- Los controllers deberían usar servicios (IncomeService, ExpenseService)
- Los servicios encapsulan lógica de negocio (ej: incluir ingresos recurrentes)
- Usar repos directamente omite esta lógica y causa bugs sutiles

Uso:
    python scripts/audit_repository_usage.py
"""

import re
from pathlib import Path

# Patrones problemáticos: repos usados directamente en controllers
PROBLEMATIC_PATTERNS = {
    # Income: siempre usar income_service.list_for_month() en controllers
    "income_repo.get_by_month": {
        "severity": "CRITICAL",
        "fix": "Usar income_service.list_for_month(year, month) en su lugar",
        "reason": "get_by_month() NO incluye ingresos recurrentes",
    },
    "income_repo.get_all": {
        "severity": "WARNING",
        "fix": "Usar income_service.list_incomes() en su lugar",
        "reason": "El servicio puede tener lógica adicional de filtrado",
    },
    # Expense: generalmente OK usar repo para gastos, pero documentar
    "expense_repo.get_by_month": {
        "severity": "INFO",
        "fix": "Considerar usar expense_service si hay lógica de negocio",
        "reason": "Los gastos recurrentes se generan automáticamente, pero verificar",
    },
    # FamilyMember: usar service para validaciones
    "member_repo.get_by_id": {
        "severity": "WARNING",
        "fix": "Usar member_service.get_member() en su lugar",
        "reason": "El servicio incluye validaciones de permisos",
    },
}

# Archivos donde NO deberíamos ver uso directo de repos
CONTROLLER_DIRS = ["controllers", "views"]

# Excepciones legítimas (repos usados en services está OK)
EXCEPTION_FILES = [
    "services/domain/",  # Services pueden usar repos directamente
    "services/ai/",  # Servicios de IA pueden usar repos
    "repositories/",  # Obvio
    "tests/",  # Tests pueden mockear repos
    "scripts/",  # Este script
]


def should_check_file(filepath: Path) -> bool:
    """Determina si un archivo debe ser auditado."""
    filepath_str = str(filepath)
    
    # Solo auditar controllers y views
    if not any(dir_name in filepath_str for dir_name in CONTROLLER_DIRS):
        return False
    
    # Excluir excepciones legítimas
    if any(exc in filepath_str for exc in EXCEPTION_FILES):
        return False
    
    return True


def audit_file(filepath: Path) -> list[dict]:
    """Audita un archivo y retorna lista de problemas encontrados."""
    findings = []
    
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")
    except Exception as e:
        return [{"error": f"No se pudo leer {filepath}: {e}"}]
    
    for line_num, line in enumerate(lines, 1):
        # Saltar comentarios
        if line.strip().startswith("#"):
            continue
        
        # Buscar patrones problemáticos
        for pattern, metadata in PROBLEMATIC_PATTERNS.items():
            if pattern in line:
                findings.append({
                    "file": filepath,
                    "line": line_num,
                    "pattern": pattern,
                    "severity": metadata["severity"],
                    "fix": metadata["fix"],
                    "reason": metadata["reason"],
                    "code": line.strip(),
                })
    
    return findings


def main():
    """Ejecuta auditoría completa."""
    print("=" * 70)
    print("AUDITOR DE ARQUITECTURA: Uso de Repositorios en Controllers")
    print("=" * 70)
    print()
    
    # Buscar todos los archivos Python
    project_root = Path(__file__).parent.parent
    py_files = list(project_root.rglob("*.py"))
    
    # Filtrar archivos a auditar
    files_to_audit = [f for f in py_files if should_check_file(f)]
    
    print(f"Archivos a auditar: {len(files_to_audit)}")
    print()
    
    # Auditar cada archivo
    all_findings = []
    for filepath in files_to_audit:
        findings = audit_file(filepath)
        all_findings.extend(findings)
    
    # Agrupar por severidad
    critical = [f for f in all_findings if f.get("severity") == "CRITICAL"]
    warnings = [f for f in all_findings if f.get("severity") == "WARNING"]
    infos = [f for f in all_findings if f.get("severity") == "INFO"]
    
    # Reportar resultados
    if critical:
        print(f"[CRITICAL] {len(critical)} problemas")
        print("-" * 70)
        for finding in critical:
            rel_path = finding["file"].relative_to(project_root)
            print(f"\n{rel_path}:{finding['line']}")
            print(f"  Patron: {finding['pattern']}")
            print(f"  Codigo: {finding['code']}")
            print(f"  Problema: {finding['reason']}")
            print(f"  Solucion: {finding['fix']}")
        print()
    
    if warnings:
        print(f"[WARNING] {len(warnings)} problemas")
        print("-" * 70)
        for finding in warnings:
            rel_path = finding["file"].relative_to(project_root)
            print(f"\n{rel_path}:{finding['line']}")
            print(f"  Patron: {finding['pattern']}")
            print(f"  Codigo: {finding['code']}")
            print(f"  Problema: {finding['reason']}")
            print(f"  Solucion: {finding['fix']}")
        print()
    
    if infos:
        print(f"[INFO] {len(infos)} observaciones")
        print("-" * 70)
        for finding in infos:
            rel_path = finding["file"].relative_to(project_root)
            print(f"\n{rel_path}:{finding['line']}")
            print(f"  Patron: {finding['pattern']}")
            print(f"  Codigo: {finding['code']}")
            print(f"  Nota: {finding['reason']}")
        print()
    
    # Resumen final
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total problemas encontrados: {len(all_findings)}")
    print(f"  - CRITICAL: {len(critical)}")
    print(f"  - WARNING: {len(warnings)}")
    print(f"  - INFO: {len(infos)}")
    print()
    
    if critical:
        print("[!] Hay problemas CRITICOS que deben corregirse inmediatamente")
        return 1
    elif warnings:
        print("[!] Hay warnings que deberian revisarse")
        return 0
    else:
        print("[OK] No se encontraron problemas de arquitectura")
        return 0


if __name__ == "__main__":
    exit(main())

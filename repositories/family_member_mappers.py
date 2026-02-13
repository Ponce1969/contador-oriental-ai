"""
Mappers para FamilyMember
"""

from __future__ import annotations

from database.tables import FamilyMemberTable
from models.family_member_model import FamilyMember


def family_member_to_domain(row: FamilyMemberTable) -> FamilyMember:
    """Convertir tabla de base de datos a modelo de dominio FamilyMember"""
    return FamilyMember(
        id=row.id,
        nombre=row.nombre,
        tipo_miembro=row.tipo_miembro if hasattr(row, 'tipo_miembro') else 'persona',
        parentesco=row.parentesco if hasattr(row, 'parentesco') else None,
        especie=row.especie if hasattr(row, 'especie') else None,
        edad=row.edad if hasattr(row, 'edad') else None,
        estado_laboral=row.estado_laboral if hasattr(row, 'estado_laboral') else None,
        activo=row.activo,
        notas=row.notas,
    )


def family_member_to_table(member: FamilyMember) -> FamilyMemberTable:
    """Convertir modelo de dominio FamilyMember a tabla de base de datos"""
    return FamilyMemberTable(
        nombre=member.nombre,
        tipo_miembro=member.tipo_miembro,
        parentesco=member.parentesco,
        especie=member.especie,
        edad=member.edad,
        estado_laboral=member.estado_laboral,
        activo=member.activo,
        notas=member.notas,
    )

"""
Mappers para FamilyMember
"""

from __future__ import annotations

from database.tables import FamilyMemberTable
from models.family_member_model import FamilyMember, IncomeType


def family_member_to_domain(row: FamilyMemberTable) -> FamilyMember:
    """Convertir tabla de base de datos a modelo de dominio FamilyMember"""
    return FamilyMember(
        id=row.id,
        nombre=row.nombre,
        tipo_ingreso=IncomeType(row.tipo_ingreso),
        sueldo_mensual=row.sueldo_mensual,
        activo=row.activo,
        notas=row.notas,
    )


def family_member_to_table(member: FamilyMember) -> FamilyMemberTable:
    """Convertir modelo de dominio FamilyMember a tabla de base de datos"""
    return FamilyMemberTable(
        nombre=member.nombre,
        tipo_ingreso=member.tipo_ingreso.value,
        sueldo_mensual=member.sueldo_mensual,
        activo=member.activo,
        notas=member.notas,
    )

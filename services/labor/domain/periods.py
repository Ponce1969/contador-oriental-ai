"""
Manejo de períodos y fechas para el cálculo laboral uruguayo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AguinaldoPeriod:
    """
    Período semestral de aguinaldo según Ley 12.840 y modificativas del MTSS.

    Fracción 1 (Junio): 1 de diciembre del año anterior al 31 de mayo del año en curso.
    Fracción 2 (Diciembre): 1 de junio al 30 de noviembre del año en curso.
    """

    year: int
    semester: int  # 1 = Junio, 2 = Diciembre
    start_date: date
    end_date: date
    payment_month: int
    payment_year: int

    @classmethod
    def for_date(cls, reference_date: date) -> AguinaldoPeriod:
        """
        Retorna el período de aguinaldo correspondiente a una fecha de referencia.

        - Si el mes está entre Diciembre y Mayo -> Fracción Junio (semestre 1).
        - Si el mes está entre Junio y Noviembre -> Fracción Diciembre (semestre 2).
        """
        year = reference_date.year
        month = reference_date.month

        if month == 12:
            # Diciembre pertenece al período del aguinaldo de junio del año siguiente
            return cls(
                year=year + 1,
                semester=1,
                start_date=date(year, 12, 1),
                end_date=date(year + 1, 5, 31),
                payment_month=6,
                payment_year=year + 1,
            )
        elif month <= 5:
            # Enero a Mayo pertenece al aguinaldo de junio de este año
            return cls(
                year=year,
                semester=1,
                start_date=date(year - 1, 12, 1),
                end_date=date(year, 5, 31),
                payment_month=6,
                payment_year=year,
            )
        else:
            # Junio a Noviembre pertenece al aguinaldo de diciembre de este año
            return cls(
                year=year,
                semester=2,
                start_date=date(year, 6, 1),
                end_date=date(year, 11, 30),
                payment_month=12,
                payment_year=year,
            )

    @classmethod
    def for_semester(cls, year: int, semester: int) -> AguinaldoPeriod:
        """Crea el período para un año y semestre específico (1 o 2)."""
        if semester == 1:
            return cls(
                year=year,
                semester=1,
                start_date=date(year - 1, 12, 1),
                end_date=date(year, 5, 31),
                payment_month=6,
                payment_year=year,
            )
        elif semester == 2:
            return cls(
                year=year,
                semester=2,
                start_date=date(year, 6, 1),
                end_date=date(year, 11, 30),
                payment_month=12,
                payment_year=year,
            )
        raise ValueError(
            f"Semestre inválido: {semester}. Debe ser 1 (Junio) o 2 (Diciembre)."
        )

    def get_months(self) -> list[tuple[int, int]]:
        """Retorna la lista ordenada de tuplas (year, month) que componen el período."""
        if self.semester == 1:
            return [
                (self.year - 1, 12),
                (self.year, 1),
                (self.year, 2),
                (self.year, 3),
                (self.year, 4),
                (self.year, 5),
            ]
        else:
            return [
                (self.year, 6),
                (self.year, 7),
                (self.year, 8),
                (self.year, 9),
                (self.year, 10),
                (self.year, 11),
            ]

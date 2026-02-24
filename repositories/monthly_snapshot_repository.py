"""
Repositorio para snapshots mensuales de gastos.
Usa SQL con window function LAG para comparativa mes a mes.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.ai_model import CategoryMetric

logger = logging.getLogger(__name__)


class MonthlySnapshotRepository:
    """Acceso a datos para historial mensual de gastos por categoría."""

    def __init__(self, session: Session, familia_id: int) -> None:
        self.session = session
        self.familia_id = familia_id

    # ------------------------------------------------------------------
    # ESCRITURA — upsert del mes actual
    # ------------------------------------------------------------------

    def upsert_mes_actual(self, anio: int, mes: int) -> int:
        """
        Calcula y guarda (INSERT OR UPDATE) las métricas del mes indicado
        directamente desde la tabla expenses.

        Returns:
            Cantidad de categorías guardadas.
        """
        sql = text("""
            INSERT INTO monthly_expense_snapshots
                (familia_id, anio, mes, categoria, total_dinero,
                 cantidad_compras, ticket_promedio)
            SELECT
                :familia_id,
                :anio,
                :mes,
                categoria,
                SUM(monto)                              AS total_dinero,
                COUNT(id)                               AS cantidad_compras,
                ROUND(SUM(monto)::NUMERIC / COUNT(id), 2) AS ticket_promedio
            FROM expenses
            WHERE familia_id = :familia_id
              AND EXTRACT(YEAR  FROM fecha) = :anio
              AND EXTRACT(MONTH FROM fecha) = :mes
            GROUP BY categoria
            ON CONFLICT (familia_id, anio, mes, categoria)
            DO UPDATE SET
                total_dinero     = EXCLUDED.total_dinero,
                cantidad_compras = EXCLUDED.cantidad_compras,
                ticket_promedio  = EXCLUDED.ticket_promedio,
                created_at       = CURRENT_TIMESTAMP
        """)

        result = self.session.execute(
            sql,
            {"familia_id": self.familia_id, "anio": anio, "mes": mes},
        )
        self.session.commit()
        count: int = result.rowcount
        logger.info(
            "Snapshot upsert: familia=%s %s/%s → %s categorías",
            self.familia_id, mes, anio, count,
        )
        return count

    # ------------------------------------------------------------------
    # LECTURA — comparativa con LAG
    # ------------------------------------------------------------------

    def obtener_comparativa_mensual(
        self,
        anio: int,
        mes: int,
        meses_atras: int = 1,
    ) -> list[CategoryMetric]:
        """
        Devuelve métricas del mes actual vs el anterior usando LAG.
        Python pre-calcula variaciones y diagnóstico; Gemma solo narra.

        Args:
            anio: Año del mes actual.
            mes: Mes actual (1-12).
            meses_atras: Cuántos meses hacia atrás comparar (default 1).

        Returns:
            Lista de CategoryMetric con variaciones ya calculadas.
        """
        sql = text("""
            WITH metricas AS (
                SELECT
                    categoria,
                    anio,
                    mes,
                    total_dinero,
                    cantidad_compras,
                    ticket_promedio,
                    LAG(total_dinero)     OVER (
                        PARTITION BY categoria ORDER BY anio, mes
                    ) AS total_anterior,
                    LAG(cantidad_compras) OVER (
                        PARTITION BY categoria ORDER BY anio, mes
                    ) AS cantidad_anterior,
                    LAG(ticket_promedio)  OVER (
                        PARTITION BY categoria ORDER BY anio, mes
                    ) AS ticket_anterior
                FROM monthly_expense_snapshots
                WHERE familia_id = :familia_id
                  AND (
                      (anio = :anio AND mes = :mes)
                      OR (anio * 12 + mes BETWEEN (:anio * 12 + :mes - :meses_atras)
                                              AND (:anio * 12 + :mes - 1))
                  )
            )
            SELECT *
            FROM metricas
            WHERE anio = :anio AND mes = :mes
            ORDER BY total_dinero DESC
        """)

        rows = self.session.execute(
            sql,
            {
                "familia_id": self.familia_id,
                "anio": anio,
                "mes": mes,
                "meses_atras": meses_atras,
            },
        ).fetchall()

        metrics: list[CategoryMetric] = []
        for row in rows:
            metric = CategoryMetric(
                categoria=row.categoria,
                mes_actual=row.mes,
                anio_actual=row.anio,
                total_actual=float(row.total_dinero),
                cantidad_actual=int(row.cantidad_compras),
                ticket_actual=float(row.ticket_promedio),
                total_anterior=float(row.total_anterior)
                if row.total_anterior is not None else None,
                cantidad_anterior=int(row.cantidad_anterior)
                if row.cantidad_anterior is not None else None,
                ticket_anterior=float(row.ticket_anterior)
                if row.ticket_anterior is not None else None,
            )
            metrics.append(metric)

        logger.info(
            "Comparativa mensual: familia=%s %s/%s → %s categorías",
            self.familia_id, mes, anio, len(metrics),
        )
        return metrics

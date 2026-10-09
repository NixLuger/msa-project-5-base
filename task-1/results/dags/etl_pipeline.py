from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta

import psycopg2
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.utils.email import send_email
from airflow.utils.trigger_rule import TriggerRule

SOURCE_DB = dict(
    host=os.environ.get("SOURCE_DB_HOST", "postgres"),
    port=int(os.environ.get("SOURCE_DB_PORT", 5432)),
    dbname=os.environ.get("SOURCE_DB_NAME", "source"),
    user=os.environ.get("SOURCE_DB_USER", "airflow"),
    password=os.environ.get("SOURCE_DB_PASSWORD", "airflow"),
)

ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "data-team@example.com")
DELIVERIES_PATH = os.environ.get("DELIVERIES_PATH", "/opt/airflow/data/deliveries.csv")


def on_dag_success(context):
    send_email(
        to=[ALERT_EMAIL],
        subject="[Airflow] ETL pipeline SUCCESS",
        html_content=(
            f"DAG <b>{context['dag'].dag_id}</b> completed successfully.<br>"
            f"Run id: {context['run_id']}"
        ),
    )


def on_dag_failure(context):
    ti = context.get("task_instance")
    send_email(
        to=[ALERT_EMAIL],
        subject="[Airflow] ETL pipeline FAILED",
        html_content=(
            f"DAG <b>{context['dag'].dag_id}</b> failed.<br>"
            f"Task: {getattr(ti, 'task_id', 'n/a')}<br>"
            f"Run id: {context['run_id']}<br>"
            f"Log: {getattr(ti, 'log_url', 'n/a')}"
        ),
    )


default_args = {
    "owner": "data-platform",
    "retries": 2,
    "retry_delay": timedelta(seconds=15),
}


with DAG(
    dag_id="etl_pipeline",
    description="POC: ETL pipeline with branching, retries and email notifications",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    on_success_callback=on_dag_success,
    on_failure_callback=on_dag_failure,
    tags=["poc", "etl", "task1"],
) as dag:

    @task
    def read_orders() -> list[dict]:
        """Шаг 1. Чтение из источника данных (PostgreSQL)."""
        with psycopg2.connect(**SOURCE_DB) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT order_id, user_id, amount, status FROM orders ORDER BY order_id"
                )
                rows = cur.fetchall()
        return [
            {
                "order_id": r[0],
                "user_id": r[1],
                "amount": float(r[2]),
                "status": r[3],
            }
            for r in rows
        ]

    @task
    def read_deliveries() -> list[dict]:
        """Шаг 2. Чтение из источника данных (файловая система, CSV)."""
        with open(DELIVERIES_PATH, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @task
    def analyze(orders: list[dict], deliveries: list[dict]) -> dict:
        """Шаг 3. Анализ данных: считаем долю заказов без доставки."""
        delivered_ids = {
            int(d["order_id"]) for d in deliveries if d.get("status") == "delivered"
        }
        total = len(orders)
        delivered = sum(1 for o in orders if o["order_id"] in delivered_ids)
        missing = total - delivered
        ratio = (missing / total) if total else 0.0
        return {
            "total_orders": total,
            "delivered": delivered,
            "missing": missing,
            "missing_ratio": round(ratio, 4),
        }

    @task.branch
    def branch_by_threshold(metrics: dict) -> str:
        """Шаг 4. Ветвление пайплайна по условию."""
        threshold = float(
            Variable.get("missing_ratio_threshold", default_var=0.1)
        )
        if metrics["missing_ratio"] > threshold:
            return "alert_path"
        return "ok_path"

    @task
    def ok_path(metrics: dict) -> str:
        return (
            f"OK: missing ratio {metrics['missing_ratio']} "
            f"<= threshold, no action required"
        )

    @task(retries=3, retry_delay=timedelta(seconds=10))
    def alert_path(metrics: dict, **context) -> str:
        """Шаг 5. Ветка проблемы. Демонстрирует retry-политику и email."""
        ti = context["ti"]
        fail_always = (
            Variable.get("alert_fail_always", default_var="false").lower() == "true"
        )
        # Симулируем нестабильный внешний API: падаем на первых попытках
        if fail_always or ti.try_number < 3:
            raise RuntimeError(
                f"Simulated transient failure on attempt {ti.try_number} "
                f"(missing_ratio={metrics['missing_ratio']})"
            )
        return (
            f"Recovered after retries on attempt {ti.try_number}. "
            f"Alert dispatched: missing ratio {metrics['missing_ratio']}"
        )

    @task(trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
    def finalize() -> str:
        return "Pipeline finished"

    orders = read_orders()
    deliveries = read_deliveries()
    metrics = analyze(orders, deliveries)
    branch = branch_by_threshold(metrics)

    ok = ok_path(metrics)
    alert = alert_path(metrics)

    branch >> [ok, alert]
    [ok, alert] >> finalize()

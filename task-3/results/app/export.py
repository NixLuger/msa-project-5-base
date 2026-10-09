"""
Простой экспорт одной таблицы PostgreSQL в CSV.

Читает данные через server-side cursor (не тянет всё в память),
пишет CSV в файл на диске.

ENV-переменные:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD — подключение к БД
    EXPORT_TABLE  — имя таблицы (по умолчанию shipments)
    OUTPUT_DIR    — каталог для CSV (по умолчанию /data/exports)
    RUN_DATE      — дата запуска в формате YYYY-MM-DD (по умолчанию сегодня, UTC)
"""
from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2 import sql

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
log = logging.getLogger("export")


def get_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        log.error("Missing required env var: %s", name)
        sys.exit(1)
    return value


def export_table_to_csv(
    conn,
    table: str,
    output_path: Path,
    batch_size: int = 5000,
) -> int:
    """Экспортирует таблицу в CSV. Возвращает число выгруженных строк."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Шаг 1. Получаем имена колонок через обычный курсор.
    # Server-side cursor (named) не отдаёт description сразу после execute,
    # поэтому запрашиваем метаданные отдельным запросом с LIMIT 0.
    with conn.cursor() as meta_cur:
        meta_cur.execute(
            sql.SQL("SELECT * FROM {} LIMIT 0").format(sql.Identifier(table))
        )
        columns = [desc[0] for desc in meta_cur.description]

    log.info("Exporting table=%s columns=%s", table, columns)

    # Шаг 2. Стримим данные через server-side cursor —
    # таблица не грузится целиком в память.
    rows_written = 0
    with conn.cursor(name="export_cursor") as cur:
        cur.itersize = batch_size
        cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table)))

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in cur:
                writer.writerow(row)
                rows_written += 1

    return rows_written


def main() -> int:
    db_host = get_env("DB_HOST", "postgres")
    db_port = int(get_env("DB_PORT", "5432"))
    db_name = get_env("DB_NAME", "analytics")
    db_user = get_env("DB_USER", "analytics")
    db_password = get_env("DB_PASSWORD")

    table = get_env("EXPORT_TABLE", "shipments")
    output_dir = Path(get_env("OUTPUT_DIR", "/data/exports"))
    run_date = get_env(
        "RUN_DATE", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    output_path = output_dir / run_date / f"{table}.csv"
    log.info("Starting export table=%s -> %s", table, output_path)

    try:
        with psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10,
        ) as conn:
            rows = export_table_to_csv(conn, table, output_path)
    except Exception as exc:
        log.error("Export failed: %s", exc)
        return 1

    log.info("Export finished rows=%d file=%s", rows, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

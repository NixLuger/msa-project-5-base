# Task 5. Метрики, логи и алерты

## 1. Метрики

Все метрики собираются через **Micrometer** и экспортируются в формате
Prometheus. Источник — Spring Boot Actuator (`/actuator/prometheus`).

### 1.1. Spring Batch Worker

| Метрика | Тип | Описание | Зачем |
|---|---|---|---|
| `spring_batch_job_duration_seconds` | Histogram | Длительность Job | SLA: 2000 строк ≤ 30 с; выявление деградации |
| `spring_batch_job_status` | Gauge | Статус последнего запуска (0 = failed, 1 = success) | Быстрый алерт на падение |
| `spring_batch_job_read_total` | Counter | Прочитано строк | Контроль объёма обработки |
| `spring_batch_job_write_total` | Counter | Записано строк | Обнаружение потерь данных |
| `spring_batch_job_skip_total` | Counter | Пропущено строк (skip policy) | Индикатор качества входящих данных |
| `spring_batch_job_retry_total` | Counter | Retry-попыток | Индикатор нестабильности внешних систем |
| `spring_batch_chunk_duration_seconds` | Histogram | Длительность обработки чанка | Поиск узких мест |
| `spring_batch_polling_runs_total` | Counter | Запусков polling-метода | Контроль работы планировщика |
| `spring_batch_polling_new_files_total` | Counter | Найдено новых файлов | Контроль потока отчётов |
| `spring_batch_polling_lag_seconds` | Gauge | Задержка между появлением файла в GCS и стартом обработки | Ключевая бизнес-метрика: «данные обновляются вовремя» |
| `spring_batch_active_jobs` | Gauge | Число одновременно выполняемых Job | Контроль параллелизма |

### 1.2. Monolith Backend (Java 11 / WildFly)

| Метрика | Тип | Описание | Зачем |
|---|---|---|---|
| `http_server_requests_seconds` | Histogram | Latency HTTP-запросов (p50/p95/p99) | SLA UI, поиск проблем производительности |
| `http_server_requests_total` | Counter | Общее число HTTP-запросов | RPS, общая нагрузка |
| `http_server_errors_total` | Counter | Ошибки HTTP (4xx/5xx) | Error rate, алерты |
| `jvm_memory_used_bytes` | Gauge | Использование heap/non-heap | Контроль утечек, OOM |
| `jvm_gc_pause_seconds` | Histogram | Паузы GC | Индикатор проблем с памятью |
| `jvm_threads_live_threads` | Gauge | Число живых потоков | Обнаружение утечек потоков |
| `hikaricp_connections_active` | Gauge | Активные соединения к БД | Контроль пула |
| `hikaricp_connections_pending` | Gauge | Ожидающие соединения | Индикатор перегрузки БД |
| `hikaricp_connection_timeout_total` | Counter | Таймауты получения соединения | Проблемы с БД |
| `process_cpu_usage` | Gauge | CPU-нагрузка процесса | Контроль ресурсов |

**Бизнес-метрики монолита:**

| Метрика | Тип | Описание | Зачем |
|---|---|---|---|
| `reports_uploaded_total` | Counter | Загружено отчётов | Бизнес-объём |
| `reports_validation_failed_total` | Counter | Отчётов с ошибкой валидации | Качество данных от клиентов |
| `report_upload_duration_seconds` | Histogram | Длительность онлайн-валидации и сохранения в GCS | SLA пользователя |

### 1.3. Инфраструктура (VM)

Собирается через **Node Exporter**.

| Метрика | Описание | Зачем |
|---|---|---|
| `node_cpu_seconds_total` | Загрузка CPU | Контроль ресурсов VM |
| `node_memory_MemAvailable_bytes` | Доступная память | Предотвращение OOM |
| `node_filesystem_avail_bytes` | Свободное место на диске | Предотвращение переполнения |
| `node_network_receive_bytes_total` / `transmit` | Сетевой трафик | Контроль нагрузки на сеть |
| `node_load1` / `node_load5` / `node_load15` | Load average | Общая нагрузка на VM |

### 1.4. PostgreSQL

Собирается через **postgres_exporter**.

| Метрика | Описание | Зачем |
|---|---|---|
| `pg_stat_activity_count` | Активные сессии | Контроль подключений |
| `pg_stat_database_tup_fetched` | Прочитано строк | Нагрузка на БД |
| `pg_stat_database_tup_updated` | Обновлено строк | Нагрузка на запись |
| `pg_stat_database_deadlocks` | Дедлоки | Проблемы с конкурентностью |
| `pg_stat_database_xact_rollback` | Откаты транзакций | Индикатор ошибок |
| `pg_database_size_bytes` | Размер БД | Контроль роста |

### 1.5. Google Cloud Storage

Собирается через **GCP-экспортер** (например, Stackdriver Exporter).

| Метрика | Описание | Зачем |
|---|---|---|
| `gcs_bucket_object_count` | Число объектов в бакете | Контроль объёма |
| `gcs_api_request_count` | Запросы к API | Нагрузка на GCS |
| `gcs_api_request_errors` | Ошибки API | Проблемы доступа |

## 2. Логи

### 2.1. Формат

Все приложения пишут логи **в stdout** в формате **JSON** (structured logging).
Поля стандартизированы.

**Обязательные поля:**

| Поле | Тип | Описание |
|---|---|---|
| `timestamp` | ISO 8601 | Время события |
| `level` | string | `INFO`, `WARN`, `ERROR`, `DEBUG` |
| `service` | string | Имя сервиса (`monolith`, `spring-batch-worker`) |
| `logger` | string | Имя логгера |
| `message` | string | Текст сообщения |
| `trace_id` | string | ID трассировки (для корреляции) |
| `span_id` | string | ID спана |

**Дополнительные поля для Spring Batch Worker:**

| Поле | Описание |
|---|---|
| `job_name` | Имя Spring Batch Job |
| `job_execution_id` | ID запуска Job |
| `step_name` | Имя шага |
| `chunk_number` | Номер чанка |
| `file_name` | Имя обрабатываемого файла из GCS |
| `rows_read` / `rows_written` / `rows_skipped` | Статистика по чанку |

**Дополнительные поля для Monolith:**

| Поле | Описание |
|---|---|
| `http_method` | HTTP-метод |
| `http_path` | Путь |
| `http_status` | Код ответа |
| `user_id` | ID пользователя (без PII) |
| `duration_ms` | Длительность запроса |

### 2.2. Что логируем

**Spring Batch Worker:**
- Старт и завершение Job с итоговой статистикой.
- Переходы между шагами.
- Начало и завершение обработки каждого файла.
- Ошибки чтения/записи/валидации.
- Срабатывания retry и skip.
- Polling: найдено N новых файлов.

**Monolith Backend:**
- Все входящие HTTP-запросы (метод, путь, статус, длительность).
- Бизнес-события: загрузка отчёта, ошибка валидации, отправка уведомления.
- Ошибки приложения с traceback.
- События подключения к БД.

### 2.3. Чего не логируем

- **Пароли, токены, ключи API.**
- **Персональные данные** (PII): ФИО, email, телефоны.
- **Содержимое файлов отчётов** — только метаданные.
- **Полные SQL-запросы с параметрами** — только шаблоны.

### 2.4. Уровни логирования

| Уровень | Когда использовать |
|---|---|
| `ERROR` | Ошибки, требующие внимания |
| `WARN` | Потенциальные проблемы (retry, skip, деградация) |
| `INFO` | Бизнес-события, старт/финиш Job |
| `DEBUG` | Только при отладке, по умолчанию выключен в проде |

### 2.5. Хранение

- **Loki** хранит логи в течение 30 дней.
- Логи старше 30 дней архивируются в GCS (lifecycle policy).
- Метки (labels): `service`, `level`, `job_name`, `environment`.

### 2.6. Сбор

- **Promtail** работает как DaemonSet на VM или sidecar-контейнер.
- Читает stdout контейнеров, парсит JSON, отправляет в Loki.
- Автоматически подхватывает метки от Docker.

## 3. Алерты

### 3.1. Правила алертов

Все алерты описаны как **PrometheusRule** (или `alerts.yml` в конфиге Prometheus).

#### Critical — требуют немедленной реакции

| Алерт | Условие | Описание |
|---|---|---|
| `BatchJobFailed` | `spring_batch_job_status == 0` | Spring Batch Job упал |
| `MonolithHighErrorRate` | `rate(http_server_errors_total[5m]) / rate(http_server_requests_total[5m]) > 0.05` | Error rate > 5% |
| `DatabaseDown` | `up{job="postgres"} == 0` | PostgreSQL недоступен |
| `GCSUnavailable` | `gcs_api_request_errors > 10` за 5 минут | GCS недоступен |
| `DiskSpaceCritical` | `node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1` | Свободно < 10% диска |
| `PollingStuck` | `time() - spring_batch_polling_last_run_timestamp > 600` | Polling не запускался > 10 минут |

#### Warning — обратить внимание в течение дня

| Алерт | Условие | Описание |
|---|---|---|
| `BatchJobSlow` | `spring_batch_job_duration_seconds > 30` для Job на 2000 строк | Превышение SLA |
| `HighLatency` | `histogram_quantile(0.95, http_server_requests_seconds) > 5` | p95 latency > 5 секунд |
| `HighJvmHeapUsage` | `jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"} > 0.9` | Heap > 90% |
| `HighGcPause` | `rate(jvm_gc_pause_seconds_sum[5m]) > 0.1` | GC-паузы > 10% времени |
| `ConnectionPoolExhausted` | `hikaricp_connections_pending > 5` | Очередь на соединения к БД |
| `BatchJobSkips` | `rate(spring_batch_job_skip_total[1h]) > 0` | Появились skipped-записи |
| `HighCpuUsage` | `rate(node_cpu_seconds_total{mode!="idle"}[5m]) > 0.85` | CPU > 85% |
| `HighMemoryUsage` | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.2` | Свободно < 20% RAM |

#### Info — информационные события

| Алерт | Условие | Описание |
|---|---|---|
| `BatchJobSucceeded` | `spring_batch_job_status == 1` (после failed) | Восстановление после падения |
| `PollingFoundFiles` | `increase(spring_batch_polling_new_files_total[1h]) > 0` | Найдены новые файлы |

### 3.2. Маршрутизация алертов

Alertmanager маршрутизирует алерты по каналам:

| Severity | Канал | Реакция |
|---|---|---|
| `critical` | Slack (#alerts-critical) + Email (on-call) | Немедленно, дежурный инженер |
| `warning` | Slack (#alerts-warning) | В течение рабочего дня |
| `info` | Slack (#alerts-info) | Без реакции, для истории |

### 3.3. Параметры группировки и дедупликации

- **Group by:** `alertname`, `service`, `severity`.
- **Group wait:** 30 секунд (собираем связанные алерты).
- **Group interval:** 5 минут.
- **Repeat interval:** 4 часа для warning, 1 час для critical.
- **Inhibition:** Если `DatabaseDown`, подавляем все алерты по этому сервису, чтобы не заспамить.

### 3.4. Пример правила в Prometheus

```yaml
groups:
  - name: spring-batch-worker
    interval: 30s
    rules:
      - alert: BatchJobFailed
        expr: spring_batch_job_status == 0
        for: 1m
        labels:
          severity: critical
          service: spring-batch-worker
        annotations:
          summary: "Spring Batch Job failed"
          description: "Job {{ $labels.job_name }} завершился с ошибкой. Проверьте логи в Grafana Loki."
          runbook_url: "https://wiki.tradeware.local/runbooks/batch-job-failed"

      - alert: BatchJobSlow
        expr: spring_batch_job_duration_seconds > 30
        for: 5m
        labels:
          severity: warning
          service: spring-batch-worker
        annotations:
          summary: "Spring Batch Job медленный"
          description: "Job {{ $labels.job_name }} выполняется {{ $value }}s при SLA ≤ 30s."
# Task 5. Мониторинг, оповещение и логирование

## Что требовалось

Спроектировать сбор и отображение метрик, выбрать и обосновать решение
для логирования и оповещения. Результат — доработанная C4-диаграмма
и документ с обоснованием метрик.

## Что сделано

| Артефакт                                           | Содержание |
|----------------------------------------------------|---|
| [`design-decisions.md`](results/design-decisions.md)     | Зафиксированные решения по стеку наблюдаемости |
| [`metrics-and-alerts.md`](results/metrics-and-alerts.md) | Метрики по контейнерам, формат и содержание логов, правила алертов, дашборды, retention |
| [`c4-с2.drawio`](./c4-diagram-monitoring.drawio)   | Исходник C4-диаграммы с мониторингом |
| [`c4-с2.png`](./c4-diagram-monitoring.png)         | Экспорт C4-диаграммы |

## Краткое резюме решения

**Стек (self-managed, в рамках GCP):**

- **Prometheus + Micrometer** — сбор и хранение метрик приложений и инфраструктуры.
- **Node Exporter** — метрики VM (CPU, RAM, disk, network).
- **Grafana** — дашборды по метрикам (PromQL) и логам (LogQL).
- **Loki + Promtail** — централизованный сбор и поиск логов.
- **Alertmanager** — маршрутизация, группировка и дедупликация алертов.
- **Каналы оповещения** — Slack (основной) + Email (эскалации).

**Почему self-managed, а не GCP-native:** в Task 4 уже принят этот стек;
добавление Alertmanager — минимальное изменение; нет vendor lock-in.

**Почему Loki, а не ELK:** легче в эксплуатации, интегрирован с Grafana,
достаточен для 400 000 строк/сутки.

**Что собираем:**

- **Spring Batch Worker:** длительность и статус Job, read/write/skip/retry,
  polling lag, активные Job.
- **Monolith Backend:** HTTP-метрики (RPS, latency, error rate),
  JVM (heap, GC, threads), HikariCP (connections, timeouts),
  бизнес-метрики (отчёты, ошибки валидации).
- **Инфраструктура:** CPU, RAM, disk, network.
- **PostgreSQL:** connections, deadlocks, rollback, размер БД.
- **GCS:** количество объектов, ошибки API.

**Что логируем:** structured JSON в stdout — timestamp, level, service,
logger, message, trace_id + доменные поля (job_name, chunk_number,
http_status и т.д.). **Не логируем:** PII, секреты, содержимое файлов.

**Алерты:** critical (падение Job, недоступность БД/GCS, error rate > 5%,
polling stuck) → Slack + Email. Warning (SLA Job, latency, heap, GC,
connections) → Slack. Info → Slack без реакции.

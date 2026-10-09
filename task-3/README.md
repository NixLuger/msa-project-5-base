# Task 3. Distributed Scheduling с k8s CronJob

## Что это

POC ежедневной выгрузки аналитических данных из PostgreSQL в CSV
через **Kubernetes CronJob**. Решение развёрнуто в **MiniKube** и
демонстрирует полный цикл: сборка Docker-образа, деплой манифестов,
автоматический запуск по расписанию, запись CSV на Persistent Volume.

## Условия задачи

- Онлайн-платформа грузоперевозок.
- Каждый день в **20:00** нужно выгружать данные в специализированное
  хранилище для аналитиков.
- Объём в проде: `shipments` ~ 50 000–200 000 строк (в POC — 50 000).
- Источник — PostgreSQL внутри K8s.
- Приёмник — CSV-файл.
- Технология — **k8s CronJob** (по условию задачи).

## Что реализовано

- **Postgres** развёрнут внутри MiniKube (Deployment + PVC + Service).
- При первом старте автоматически создаётся таблица `shipments`
  и заливаются 50 000 строк тестовых данных.
- **CronJob** запускается по расписанию `0 20 * * *` (Europe/Moscow).
- Под экспорта читает таблицу через **server-side cursor** (не грузит
  всё в память) и пишет CSV на **PVC**.
- Файлы сохраняются по пути `/data/{YYYY-MM-DD}/shipments.csv`
  — идемпотентно по дате.
- **Debug-pod** монтирует тот же PVC, чтобы проверить результат.

## Структура проекта

```
Task3/
├── README.md
├── app/
│   ├── export.py              # скрипт экспорта
│   ├── requirements.txt
│   └── Dockerfile
├── k8s/
│   ├── namespace.yaml
│   ├── postgres-secret.yaml
│   ├── postgres-init-configmap.yaml
│   ├── postgres-pvc.yaml
│   ├── postgres-deployment.yaml
│   ├── postgres-service.yaml
│   ├── export-pvc.yaml
│   ├── export-cronjob.yaml
│   └── debug-pod.yaml
└── screenshots/
    ├── 01_minikube_nodes.png
    ├── 02_namespace_resources.png
    ├── 03_cronjob_definition.png
    ├── 04_auto_jobs.png
    ├── 05_job_logs.png
    ├── 06_pods.png
    ├── 07_pvc_files.png
    ├── 08_csv_head.png
    ├── 09_csv_wc.png
    └── 10_postgres_count.png
```

## Архитектура

```
┌──────────────────── namespace: task3 ─────────────────────┐
│                                                            │
│   ┌──────────────────┐        ┌──────────────────────┐     │
│   │  Postgres Pod    │◄───────│  CronJob Pod         │     │
│   │  (Deployment)    │  SELECT│  shipments-export    │     │
│   │  shipments table │        │  (Python 3.11)       │     │
│   └────────┬─────────┘        └──────────┬───────────┘     │
│            │                             │                 │
│       ┌────▼─────┐                  ┌────▼─────┐           │
│       │postgres- │                  │export-pvc│           │
│       │  pvc     │                  │(CSV)     │           │
│       └──────────┘                  └────┬─────┘           │
│                                          │                 │
│                                     ┌────▼─────┐           │
│                                     │ debug-   │           │
│                                     │ pod      │           │
│                                     └──────────┘           │
└────────────────────────────────────────────────────────────┘
```

## Как развернуть в MiniKube

### Требования

- MiniKube (v1.35+)
- kubectl
- Docker

Проверка:

```bash
minikube status
kubectl get nodes
```

### Шаг 1. Запустить MiniKube

```bash
minikube start --driver=docker
```

### Шаг 2. Собрать и загрузить образ

```bash
cd app
docker build -t shipments-export:latest .
minikube image load shipments-export:latest
```

Проверка:

```bash
minikube image ls | grep shipments-export
```

### Шаг 3. Применить манифесты

```bash
cd ../k8s

# Сначала namespace
kubectl apply -f namespace.yaml

# Затем всё остальное
kubectl apply -f .
```

### Шаг 4. Дождаться готовности Postgres

```bash
kubectl get pods -n task3 -w
```

Ждём, пока `postgres-xxx` перейдёт в `Running` и `READY 1/1`.
На первом старте занимает 30–60 секунд (создание таблицы + 50 000 строк).

Проверка:

```bash
kubectl exec -n task3 deploy/postgres -- \
  psql -U analytics -d analytics -c "SELECT count(*) FROM shipments;"
# Ожидаемо: 50000
```

## Как запустить вручную

CronJob по умолчанию ждёт 20:00. Для теста — ручной запуск:

```bash
kubectl create job --from=cronjob/shipments-export \
  shipments-export-manual -n task3
```

Логи:

```bash
kubectl logs -n task3 -l job-name=shipments-export-manual
```

Ожидаемо:

```
{"ts":"...","level":"INFO","msg":"Starting export table=shipments -> /data/exports/YYYY-MM-DD/shipments.csv"}
{"ts":"...","level":"INFO","msg":"Exporting table=shipments columns=[...]"}
{"ts":"...","level":"INFO","msg":"Export finished rows=50000 file=..."}
```

## Как проверить результат (CSV)

Файл лежит на PVC. Проверяем через `debug-pod`:

```bash
# Список файлов
kubectl exec -n task3 debug-pod -- ls -lh /data/$(date +%F)/

# Первые 3 строки CSV
kubectl exec -n task3 debug-pod -- head -3 /data/$(date +%F)/shipments.csv

# Число строк (ожидаем 50001)
kubectl exec -n task3 debug-pod -- wc -l /data/$(date +%F)/shipments.csv
```

## Как проверить автоматический запуск CronJob

CronJob запустится сам в 20:00 по Москве. Если не хочется ждать —
можно временно изменить расписание на «каждую минуту»:

```bash
# Временно
kubectl patch cronjob shipments-export -n task3 --type=json -p='[{"op":"replace","path":"/spec/schedule","value":"* * * * *"}]'

# Подождать 1-2 минуты
sleep 90
kubectl get jobs -n task3

# Посмотреть логи свежего Job
kubectl logs -n task3 job/<имя-свежего-job>

# вернуть обратно!
kubectl patch cronjob shipments-export -n task3 --type=json -p='[{"op":"replace","path":"/spec/schedule","value":"0 20 * * *"}]'
```

## Ключевые архитектурные решения

| Решение | Зачем |
|---|---|
| **CronJob, а не Deployment + планировщик внутри** | Расписание — родная функция K8s, не требует собственного scheduler’а |
| **`concurrencyPolicy: Forbid`** | Защита от параллельного запуска, если предыдущий Job завис |
| **`backoffLimit: 2`** | Два retry при ошибке (транзиентные сбои БД/сети) |
| **`activeDeadlineSeconds: 1800`** | Таймаут 30 минут — защита от «вечного» зависания |
| **`startingDeadlineSeconds: 600`** | Не запускать Job, если по каким-то причинам старт пропущен более 10 минут назад |
| **`timeZone: Europe/Moscow`** | Чтобы «20:00» означало московское время, а не UTC |
| **Server-side cursor (`psycopg2`)** | Таблица не грузится в память целиком — критично для миллионов строк |
| **Идемпотентность по дате** | Путь `/data/exports/{YYYY-MM-DD}/shipments.csv`. Повторный запуск за ту же дату перезапишет файл, а не создаст дубликат |
| **Non-root user в контейнере** | `runAsUser: 1000`, `runAsNonRoot: true` — базовое требование безопасности |
| **`subPath: pgdata`** для PVC Postgres | Обход проблемы с `lost+found` в некоторых volume-провайдерах |
| **`readinessProbe` через `pg_isready`** | CronJob не стартует раньше, чем Postgres готов принимать соединения |

## Скриншоты работы

Все скриншоты лежат в `screenshots/`:

| Файл | Что показывает |
|---|---|
| `01_minikube_nodes.png` | MiniKube запущен, узел `Ready` |
| `02_namespace_resources.png` | Все ресурсы Task 3 в одном namespace |
| `03_cronjob_definition.png` | Полный YAML CronJob (расписание, политики) |
| `04_auto_jobs.png` | CronJob сам создал несколько Job-ов по расписанию |
| `05_job_logs.png` | Логи успешного экспорта: `rows=50000` |
| `06_pods.png` | Поды: Postgres, debug, завершённые Job-поды |
| `07_pvc_files.png` | Файл `shipments.csv` (5.3 МБ) на PVC |
| `08_csv_head.png` | Заголовок и первые строки CSV |
| `09_csv_wc.png` | `50001` строка в CSV |
| `10_postgres_count.png` | `50000` строк в источнике (Postgres) |

## Как всё убрать

Удалить весь namespace со всеми ресурсами

```bash
kubectl delete namespace task3
```

Или по отдельности:

```bash
kubectl delete -f k8s/
```

Остановить MiniKube:

```bash
minikube stop
```
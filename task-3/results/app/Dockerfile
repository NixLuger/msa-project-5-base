FROM python:3.11-slim

# Non-root user
RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY export.py .

USER app

# По умолчанию пишем в PVC
ENV OUTPUT_DIR=/data/exports

ENTRYPOINT ["python", "/app/export.py"]

FROM python:3.11-slim

LABEL maintainer="Prefect Prometheus Exporter"
LABEL description="Exporteur de métriques Prefect pour Prometheus"

ENV EXPORTER_PORT=8080
ENV EXPORTER_INTERVAL=30
ENV LOOKBACK_HOURS=24
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

RUN addgroup --gid 1001 exporter && \
    adduser --uid 1001 --gid 1001 --disabled-password --gecos "" exporter

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

USER exporter

EXPOSE ${EXPORTER_PORT}

CMD ["python", "exporter.py"]

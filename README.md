# Prefect Prometheus Exporter

Exporteur de métriques Prefect au format Prometheus.

## Métriques exposées

### Flow Runs
- `prefect_flow_runs_total{flow_name, state}` - Nombre de runs par état
- `prefect_flow_runs_active{flow_name}` - Runs actifs (RUNNING, PENDING, SCHEDULED)
- `prefect_flow_runs_success_total{flow_name}` - Compteur de succès
- `prefect_flow_runs_failed_total{flow_name}` - Compteur d'échecs

### Task Runs
- `prefect_task_runs_total{task_name, flow_name, state}` - Nombre de runs par état
- `prefect_task_runs_success_total{task_name, flow_name}` - Compteur de succès
- `prefect_task_runs_failed_total{task_name, flow_name}` - Compteur d'échecs

### Ressources
- `prefect_flows_count` - Nombre total de flows
- `prefect_deployments_count` - Nombre total de déploiements

## Configuration

Variables d'environnement :

- `EXPORTER_PORT` - Port HTTP (défaut: 8080)
- `EXPORTER_INTERVAL` - Intervalle de collecte en secondes (défaut: 30)
- `LOOKBACK_HOURS` - Fenêtre temporelle en heures (défaut: 24)
- `LOG_LEVEL` - Niveau de log (défaut: INFO)
- `PREFECT_API_URL` - URL de l'API Prefect
- `PREFECT_API_KEY` - Clé d'API Prefect (si nécessaire)

## Utilisation

### Local

```bash
pip install -r requirements.txt
export PREFECT_API_URL=http://localhost:4200/api
python exporter.py
```

### Docker

```bash
docker build -t prefect-exporter .
docker run -p 8080:8080 \
  -e PREFECT_API_URL=http://prefect:4200/api \
  prefect-exporter
```

### Docker Compose

```yaml
services:
  prefect-exporter:
    image: prefect-exporter
    ports:
      - "8080:8080"
    environment:
      PREFECT_API_URL: http://prefect:4200/api
      EXPORTER_INTERVAL: 30
      LOOKBACK_HOURS: 24
```

## Accès aux métriques

```bash
curl http://localhost:8080/metrics
```

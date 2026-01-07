# Prefect Prometheus Exporter

Exporteur de métriques Prefect au format Prometheus.

# Prefect Prometheus Exporter

Exporteur simple qui expose des métriques Prefect au format Prometheus.

## Métriques exposées

- `prefect_exporter_collect_errors_total` (Counter)
  : Nombre total d'erreurs survenues lors des collectes.

- `prefect_flow_runs_total` (Gauge)
  : Nombre total de flow runs (valeur entière).

- `prefect_flow_runs_successes_total` (Gauge)
  : Nombre total de flow runs terminés avec succès. États considérés : Completed, Cached.

- `prefect_flow_runs_in_error_total` (Gauge)
  : Nombre total de flow runs dans un état d'erreur. États considérés : RolledBack, Failed, TimedOut, Crashed, Suspended.

- `prefect_flow_runs_in_warning_total` (Gauge)
  : Nombre total de flow runs dans un état d'avertissement. États considérés : Cancelling, Cancelled, Paused, Retrying.

- `prefect_missing_deployments_total` (Gauge)
  : Nombre de déploiements surveillés manquants (contrôle basé sur la liste fournie via `EXPORTER_CHECK_DEPLOYMENTS`).

Remarque : ces métriques sont exposées sans labels supplémentaires par la version actuelle du code.

## Configuration

Variables d'environnement principales :


- `PREFECT_API_URL` : URL de l'API Prefect.
- `PREFECT_API_AUTH_STRING` : chaîne d'authentification pour l'API Prefect.
- *autres variables d'environnement pour configurer le client prefect à votre guise.*

- `EXPORTER_PORT` : port HTTP exposé (par défaut 8080).
- `EXPORTER_INTERVAL` : intervalle de collecte en secondes (par défaut 30).
- `LOG_LEVEL` : niveau de log (`INFO` par défaut).
- `EXPORTER_CHECK_DEPLOYMENTS` : liste (séparée par des virgules) de noms de flows à vérifier pour l'existence de déploiements. Exemple : `flow-a,flow-b`.

Le client Prefect utilisé par l'exporter s'appuie sur la configuration de Prefect (variables d'environnement ou configuration client). Assurez-vous que l'accès à l'API Prefect est correctement configuré pour l'environnement cible.

## Utilisation

Local (venv) :

```bash
pip install -r requirements.txt
# Exemple : vérifier les déploiements "flow-a" et "flow-b"
export EXPORTER_CHECK_DEPLOYMENTS=flow-a,flow-b
export EXPORTER_PORT=8080
python exporter.py
```

Docker :

```bash
docker build -t prefect-exporter .
docker run -p 8080:8080 \
  -e EXPORTER_CHECK_DEPLOYMENTS="flow-a,flow-b" \
  -e EXPORTER_INTERVAL=30 \
  prefect-exporter
```

Accéder aux métriques :

```bash
curl http://localhost:8080/metrics
```

## Notes

- Le format et les métriques sont volontairement simples : chaque métrique est mise à jour périodiquement par l'exporter.
- Si vous souhaitez ajouter des labels (ex. flow_name), il faudra étendre les classes métriques dans `metrics_flow_runs.py` / `metrics_deployment.py`.

Si quelque chose n'est pas clair ou si vous voulez que j'ajoute un exemple Docker Compose ou des instructions de déploiement systemd, dites-le simplement.

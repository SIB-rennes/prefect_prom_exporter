#!/usr/bin/env python3
"""
Prefect Prometheus Exporter

Expose les métriques Prefect au format Prometheus.
Collecte les informations sur les flows, tasks et leurs statuts.
"""

import asyncio
import time
import logging
import os
from prefect.client.orchestration import get_client
from prometheus_client import Counter, start_http_server
from prometheus_client.core import CollectorRegistry

from metrics_flow_runs import (
    metric_flow_runs,
    metric_flow_success,
    metric_flow_in_error,
    metric_flow_in_warning,
)
from metrics_deployment import metric_missing_deployments

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

EXPORTER_CHECK_DEPLOYMENTS = str(os.getenv("EXPORTER_CHECK_DEPLOYMENTS", "")).split(",")


class PrefectExporter:
    """Exporteur de métriques Prefect pour Prometheus"""

    def __init__(self, port: int = 8080, interval: int = 30):
        """
        Args:
            port: Port d'écoute
            interval: Intervalle de collecte (secondes)
            lookback_hours: Fenêtre de temps pour les métriques (heures)
        """
        self.port = port
        self.interval = interval
        self.registry = CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self):
        """Configure les métriques Prometheus"""

        self.collect_errors = Counter(
            "prefect_exporter_collect_errors_total",
            "Nombre total d'erreurs lors de la collecte des métriques",
            registry=self.registry,
        )

        self.metrics = [
            metric_flow_runs(),
            metric_flow_success(),
            metric_flow_in_error(),
            metric_flow_in_warning(),
            metric_missing_deployments(EXPORTER_CHECK_DEPLOYMENTS),
        ]

        for metric in self.metrics:
            metric.register_metric(self.registry)

    async def run(self):
        """Lance l'exporteur"""
        import asyncio

        logger.info(f"Démarrage sur le port {self.port}")

        start_http_server(self.port, registry=self.registry)
        logger.info(f"Serveur disponible sur http://0.0.0.0:{self.port}/metrics")

        # Boucle principale
        previous = int(time.time())
        while True:
            try:
                logger.info("Collecte des métriques Prefect")
                now = int(time.time())
                async with get_client() as client:
                    tasks = [
                        metric.collect(client, now - previous)
                        for metric in self.metrics
                    ]

                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=self.interval - 1,
                    )

                for result in results:
                    if isinstance(result, Exception):
                        logger.error(
                            f"Erreur lors de la collecte des métriques: {result}",
                            exc_info=True,
                        )
                        self.collect_errors.inc()

            except KeyboardInterrupt:
                logger.info("Arrêt demandé")
                break
            except Exception as e:
                logger.error(f"Erreur boucle principale: {e}", exc_info=True)
                logger.info(f"Nouvelle tentative dans {self.interval}s")
                self.collect_errors.inc()
            finally:
                previous = now
                time.sleep(self.interval)


async def main():
    """Point d'entrée"""
    port = int(os.getenv("EXPORTER_PORT", "8080"))
    interval = int(os.getenv("EXPORTER_INTERVAL", "30"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, log_level, logging.INFO)
    logging.getLogger().setLevel(numeric_level)

    logger.info(f"Configuration: port={port}, interval={interval}s")
    logger.info(f"Vérification des déploiements suivants: {EXPORTER_CHECK_DEPLOYMENTS}")

    exporter = PrefectExporter(port=port, interval=interval)
    await exporter.run()


if __name__ == "__main__":
    asyncio.run(main())

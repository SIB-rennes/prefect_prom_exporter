#!/usr/bin/env python3
"""
Prefect Prometheus Exporter

Expose les métriques Prefect au format Prometheus.
Collecte les informations sur les flows, tasks et leurs statuts.
"""

import time
import logging
import os
from typing import Dict, List
from datetime import datetime, timedelta
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import FlowRunFilter, TaskRunFilter, FlowRunFilterState, TaskRunFilterState
from prefect.client.schemas.objects import StateType
from prometheus_client import Gauge, Counter, start_http_server
from prometheus_client.core import CollectorRegistry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PrefectExporter:
    """Exporteur de métriques Prefect pour Prometheus"""
    
    def __init__(self, port: int = 8080, interval: int = 30, lookback_hours: int = 24):
        """
        Args:
            port: Port d'écoute
            interval: Intervalle de collecte (secondes)
            lookback_hours: Fenêtre de temps pour les métriques (heures)
        """
        self.port = port
        self.interval = interval
        self.lookback_hours = lookback_hours
        self.registry = CollectorRegistry()
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Configure les métriques Prometheus"""
        
        # Flow runs
        self.flow_runs_total = Gauge(
            'prefect_flow_runs_total',
            'Nombre total de flow runs par état',
            ['flow_name', 'state'],
            registry=self.registry
        )
        
        self.flow_runs_active = Gauge(
            'prefect_flow_runs_active',
            'Nombre de flow runs actifs',
            ['flow_name'],
            registry=self.registry
        )
        
        self.flow_runs_success_count = Counter(
            'prefect_flow_runs_success_total',
            'Compteur de flow runs réussis',
            ['flow_name'],
            registry=self.registry
        )
        
        self.flow_runs_failed_count = Counter(
            'prefect_flow_runs_failed_total',
            'Compteur de flow runs échoués',
            ['flow_name'],
            registry=self.registry
        )
        
        # Task runs
        self.task_runs_total = Gauge(
            'prefect_task_runs_total',
            'Nombre total de task runs par état',
            ['task_name', 'flow_name', 'state'],
            registry=self.registry
        )
        
        self.task_runs_success_count = Counter(
            'prefect_task_runs_success_total',
            'Compteur de task runs réussies',
            ['task_name', 'flow_name'],
            registry=self.registry
        )
        
        self.task_runs_failed_count = Counter(
            'prefect_task_runs_failed_total',
            'Compteur de task runs échouées',
            ['task_name', 'flow_name'],
            registry=self.registry
        )
        
        # Métriques générales
        self.flows_count = Gauge(
            'prefect_flows_count',
            'Nombre total de flows déployés',
            registry=self.registry
        )
        
        self.deployments_count = Gauge(
            'prefect_deployments_count',
            'Nombre total de déploiements',
            registry=self.registry
        )
    
    async def collect_metrics(self):
        """Collecte les métriques Prefect"""
        try:
            logger.info("Collecte des métriques Prefect...")
            
            async with get_client() as client:
                # Fenêtre temporelle
                since = datetime.now() - timedelta(hours=self.lookback_hours)
                
                # Réinitialisation des gauges
                self.flow_runs_total.clear()
                self.flow_runs_active.clear()
                self.task_runs_total.clear()
                
                # Collecte des flow runs
                await self._collect_flow_runs(client, since)
                
                # Collecte des task runs
                await self._collect_task_runs(client, since)
                
                # Collecte des déploiements
                await self._collect_deployments(client)
                
            logger.info("Collecte terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte: {e}", exc_info=True)
    
    async def _collect_flow_runs(self, client, since: datetime):
        """Collecte les métriques des flow runs"""
        try:
            # Récupération de tous les flow runs récents
            flow_runs = await client.read_flow_runs(
                limit=1000,
                sort='START_TIME_DESC'
            )
            
            # Compteurs par flow et par état
            flow_stats: Dict[str, Dict[str, int]] = {}
            flow_active: Dict[str, int] = {}
            
            # Mémorisation des états précédents pour les counters
            if not hasattr(self, '_previous_flow_success'):
                self._previous_flow_success = {}
                self._previous_flow_failed = {}
            
            for run in flow_runs:
                if run.start_time and run.start_time < since:
                    continue
                
                flow_name = run.flow_name or 'unknown'
                state = run.state.type.value if run.state else 'unknown'
                
                # Initialisation des dictionnaires
                if flow_name not in flow_stats:
                    flow_stats[flow_name] = {}
                    flow_active[flow_name] = 0
                
                # Comptage par état
                flow_stats[flow_name][state] = flow_stats[flow_name].get(state, 0) + 1
                
                # Flow runs actifs (RUNNING, PENDING, SCHEDULED)
                if run.state and run.state.type in [StateType.RUNNING, StateType.PENDING, StateType.SCHEDULED]:
                    flow_active[flow_name] += 1
                
                # Compteurs de succès/échec
                key = f"{flow_name}:{run.id}"
                if run.state and run.state.type == StateType.COMPLETED:
                    if key not in self._previous_flow_success:
                        self.flow_runs_success_count.labels(flow_name=flow_name).inc()
                        self._previous_flow_success[key] = True
                elif run.state and run.state.type == StateType.FAILED:
                    if key not in self._previous_flow_failed:
                        self.flow_runs_failed_count.labels(flow_name=flow_name).inc()
                        self._previous_flow_failed[key] = True
            
            # Mise à jour des gauges
            for flow_name, states in flow_stats.items():
                for state, count in states.items():
                    self.flow_runs_total.labels(flow_name=flow_name, state=state).set(count)
            
            for flow_name, count in flow_active.items():
                self.flow_runs_active.labels(flow_name=flow_name).set(count)
            
            logger.info(f"Flow runs collectés: {len(flow_runs)} runs, {len(flow_stats)} flows")
            
        except Exception as e:
            logger.error(f"Erreur collecte flow runs: {e}", exc_info=True)
    
    async def _collect_task_runs(self, client, since: datetime):
        """Collecte les métriques des task runs"""
        try:
            # Récupération des task runs récentes
            task_runs = await client.read_task_runs(
                limit=1000,
                sort='START_TIME_DESC'
            )
            
            # Compteurs par task et par état
            task_stats: Dict[tuple, Dict[str, int]] = {}
            
            # Mémorisation des états précédents pour les counters
            if not hasattr(self, '_previous_task_success'):
                self._previous_task_success = {}
                self._previous_task_failed = {}
            
            for run in task_runs:
                if run.start_time and run.start_time < since:
                    continue
                
                task_name = run.task_name or 'unknown'
                flow_name = 'unknown'
                
                # Récupération du flow name si disponible
                if run.flow_run_id:
                    try:
                        flow_run = await client.read_flow_run(run.flow_run_id)
                        flow_name = flow_run.flow_name or 'unknown'
                    except:
                        pass
                
                state = run.state.type.value if run.state else 'unknown'
                key_tuple = (task_name, flow_name)
                
                # Initialisation
                if key_tuple not in task_stats:
                    task_stats[key_tuple] = {}
                
                # Comptage par état
                task_stats[key_tuple][state] = task_stats[key_tuple].get(state, 0) + 1
                
                # Compteurs de succès/échec
                run_key = f"{task_name}:{flow_name}:{run.id}"
                if run.state and run.state.type == StateType.COMPLETED:
                    if run_key not in self._previous_task_success:
                        self.task_runs_success_count.labels(task_name=task_name, flow_name=flow_name).inc()
                        self._previous_task_success[run_key] = True
                elif run.state and run.state.type == StateType.FAILED:
                    if run_key not in self._previous_task_failed:
                        self.task_runs_failed_count.labels(task_name=task_name, flow_name=flow_name).inc()
                        self._previous_task_failed[run_key] = True
            
            # Mise à jour des gauges
            for (task_name, flow_name), states in task_stats.items():
                for state, count in states.items():
                    self.task_runs_total.labels(
                        task_name=task_name,
                        flow_name=flow_name,
                        state=state
                    ).set(count)
            
            logger.info(f"Task runs collectées: {len(task_runs)} runs, {len(task_stats)} tasks")
            
        except Exception as e:
            logger.error(f"Erreur collecte task runs: {e}", exc_info=True)
    
    async def _collect_deployments(self, client):
        """Collecte les métriques des déploiements"""
        try:
            # Nombre de déploiements
            deployments = await client.read_deployments()
            self.deployments_count.set(len(deployments))
            
            # Nombre de flows uniques
            flows = await client.read_flows()
            self.flows_count.set(len(flows))
            
            logger.info(f"Déploiements: {len(deployments)}, Flows: {len(flows)}")
            
        except Exception as e:
            logger.error(f"Erreur collecte déploiements: {e}", exc_info=True)
    
    def run(self):
        """Lance l'exporteur"""
        import asyncio
        
        logger.info(f"Démarrage sur le port {self.port}")
        
        start_http_server(self.port, registry=self.registry)
        logger.info(f"Serveur disponible sur http://0.0.0.0:{self.port}/metrics")
        
        # Boucle principale
        while True:
            try:
                asyncio.run(self.collect_metrics())
                logger.debug(f"Attente de {self.interval}s")
                time.sleep(self.interval)
            except KeyboardInterrupt:
                logger.info("Arrêt demandé")
                break
            except Exception as e:
                logger.error(f"Erreur boucle principale: {e}", exc_info=True)
                logger.info(f"Nouvelle tentative dans {self.interval}s")
                time.sleep(self.interval)

def main():
    """Point d'entrée"""
    port = int(os.getenv('EXPORTER_PORT', '8080'))
    interval = int(os.getenv('EXPORTER_INTERVAL', '30'))
    lookback_hours = int(os.getenv('LOOKBACK_HOURS', '24'))
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    numeric_level = getattr(logging, log_level, logging.INFO)
    logging.getLogger().setLevel(numeric_level)
    
    logger.info(f"Configuration: port={port}, interval={interval}s, lookback={lookback_hours}h")
    
    exporter = PrefectExporter(port=port, interval=interval, lookback_hours=lookback_hours)
    exporter.run()

if __name__ == '__main__':
    main()

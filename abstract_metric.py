
from abc import ABC, abstractmethod

from prefect.client.orchestration import PrefectClient

from prometheus_client import CollectorRegistry
from prometheus_client.metrics import MetricWrapperBase


class AbstractMetric(ABC):
    
    @abstractmethod
    def register_metric(self, registry: CollectorRegistry) -> MetricWrapperBase:
        """Create prometheus metric and registers it to the registry."""
        pass
    
    @abstractmethod
    async def collect(self, client: PrefectClient, since: int):
        """
        Docstring pour collect
        
        :param client: client prefect
        :type client: PrefectClient
        :param since: temps en secondes depuis la dernière collecte, 0 si première collecte
        :type since: int
        """
        pass

from prefect.client.orchestration import PrefectClient
from prometheus_client import Gauge
from abstract_metric import AbstractMetric

from prefect.client.schemas.filters import FlowFilter
from prefect.client.schemas.filters import FlowFilterName
from prefect.client.schemas.objects import DeploymentStatus

def metric_missing_deployments(deployments: list[str]):
    return MetricMissingDeployments(deployments)

class MetricMissingDeployments(AbstractMetric):
    
    def __init__(self, deployments: list[str]) -> None:
        super().__init__()
        self._deployment_names = deployments
     
    def register_metric(self, registry):

        self._deployments_total = Gauge(
            "prefect_missing_deployments_total",
            f"Nombre de déploiements manquant dans l'instance prefect (déploiements surveillés: {', '.join(self._deployment_names)})",
            registry=registry,
        )
        return self._deployments_total
    
    async def collect(self, client: PrefectClient, since: int):
        ff = FlowFilter(
            name=FlowFilterName(any_=self._deployment_names),  # type: ignore
        )
        
        corresponding_deployments = await client.read_deployments(flow_filter=ff)
        corresponding_deployments = [
            d for d in corresponding_deployments if d.status == DeploymentStatus.READY
        ]

        nb_deployments = len(corresponding_deployments)
        nb_missing_deployments = len(self._deployment_names) - nb_deployments

        self._deployments_total.set(nb_missing_deployments)
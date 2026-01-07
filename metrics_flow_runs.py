from prefect.client.orchestration import PrefectClient
from prefect.client.schemas.filters import FlowRunFilter
from prefect.client.schemas.filters import FlowRunFilterState, FlowRunFilterStateName

from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.metrics import MetricWrapperBase
from abstract_metric import AbstractMetric


def metric_flow_runs():
    return MetricFlowRuns()


class MetricFlowRuns(AbstractMetric):
    def register_metric(self, registry):
        self._flow_runs_total = Gauge(
            "prefect_flow_runs_total",
            "Nombre total de flow runs",
            registry=registry,
        )
        return self._flow_runs_total

    async def collect(self, client, since):
        nb_flow_runs = await client.count_flow_runs()
        self._flow_runs_total.set(nb_flow_runs)


###############################################################
# Sur les status des flow
# https://docs.prefect.io/v3/concepts/states#state-types
#
def metric_flow_success():
    return MetricFlowInSuccess()


SUCCESS_STATES_NAMES = ["Completed", "Cached"]
IN_ERROR_STATES_NAMES = ["RolledBack", "Failed", "TimedOut", "Crashed", "Suspended"]
IN_WARNING_STATES_NAMES = ["Cancelling", "Cancelled", "Paused", "Retrying"]


class MetricFlowInSuccess(AbstractMetric):
    def register_metric(self, registry):
        self._flow_run_successes_total = Gauge(
            "prefect_flow_runs_successes_total",
            f"Nombre total de flow runs qui se sont terminés correctement . ({', '.join(SUCCESS_STATES_NAMES)})",
            registry=registry,
        )
        return self._flow_run_successes_total

    async def collect(self, client, since):
        flow_run_filter = FlowRunFilter(
            state=FlowRunFilterState(
                name=FlowRunFilterStateName(any_=SUCCESS_STATES_NAMES),  # type: ignore
            )
        )
        nb_flow_runs_successes = await client.count_flow_runs(
            flow_run_filter=flow_run_filter
        )  # type: ignore

        self._flow_run_successes_total.set(nb_flow_runs_successes)


###############################################################
#
def metric_flow_in_error():
    return MetricFlowInErrorState()


class MetricFlowInErrorState(AbstractMetric):
    def register_metric(self, registry: CollectorRegistry) -> MetricWrapperBase:
        self._metric = Gauge(
            "prefect_flow_runs_in_error_total",
            f"Nombre total de flow runs dans un état d'erreur. ({', '.join(IN_ERROR_STATES_NAMES)})",
            registry=registry,
        )
        return self._metric

    async def collect(self, client: PrefectClient, since: int):
        n = await client.count_flow_runs(
            flow_run_filter=FlowRunFilter(
                state=FlowRunFilterState(
                    name=FlowRunFilterStateName(any_=IN_ERROR_STATES_NAMES),  # type: ignore
                )
            )
        )  # type: ignore
        self._metric.set(n)


###############################################################
#
def metric_flow_in_warning():
    return MetricFlowInWarningState()


class MetricFlowInWarningState(AbstractMetric):
    def register_metric(self, registry: CollectorRegistry) -> MetricWrapperBase:
        self._metric = Gauge(
            "prefect_flow_runs_in_warning_total",
            f"Nombre total de flow runs dans un état d'avertissement. ({', '.join(IN_WARNING_STATES_NAMES)})",
            registry=registry,
        )
        return self._metric

    async def collect(self, client: PrefectClient, since: int):
        n = await client.count_flow_runs(
            flow_run_filter=FlowRunFilter(
                state=FlowRunFilterState(
                    name=FlowRunFilterStateName(any_=IN_WARNING_STATES_NAMES),  # type: ignore
                )
            )
        )  # type: ignore
        self._metric.set(n)

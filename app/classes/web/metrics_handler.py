import logging
import typing as t

from prometheus_client import REGISTRY, CollectorRegistry
from prometheus_client.exposition import _bake_output
from prometheus_client.exposition import parse_qs, urlparse

from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class BaseMetricsHandler(BaseApiHandler):
    """HTTP handler that gives metrics from ``REGISTRY``."""

    registry: CollectorRegistry = REGISTRY
    # registry.unregister(GC_COLLECTOR)
    # registry.unregister(PLATFORM_COLLECTOR)
    # registry.unregister(PROCESS_COLLECTOR)

    def get_registry(self) -> None:
        # Prepare parameters
        registry = self.registry
        accept_header = self.request.headers.get("Accept")
        accept_encoding_header = self.request.headers.get("Accept-Encoding")
        params = parse_qs(urlparse(self.request.path).query)
        # Bake output
        status, headers, output = _bake_output(
            registry, accept_header, accept_encoding_header, params, False
        )
        # Return output
        self.finish_metrics(int(status.split(" ", maxsplit=1)[0]), headers, output)

    @classmethod
    def factory(cls, registry: CollectorRegistry) -> type:
        """Returns a dynamic MetricsHandler class tied
        to the passed registry.
        """
        # This implementation relies on MetricsHandler.registry
        #  (defined above and defaulted to REGISTRY).

        # As we have unicode_literals, we need to create a str()
        #  object for type().
        cls_name = str(cls.__name__)
        MyMetricsHandler = type(cls_name, (cls, object), {"registry": registry})
        return MyMetricsHandler

    def finish_metrics(self, status: int, headers, data: t.Dict[str, t.Any]):
        self.set_status(status)
        self.set_header("Content-Type", "text/plain")
        for header in headers:
            self.set_header(*header)
        self.finish(data)

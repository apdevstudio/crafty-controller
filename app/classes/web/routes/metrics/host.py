from prometheus_client.exposition import _bake_output
from prometheus_client.exposition import parse_qs, urlparse

from app.classes.web.metrics_handler import BaseMetricsHandler


# Decorate function with metric.
class ApiOpenMetricsCraftyHandler(BaseMetricsHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if not auth_data[3]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.get_registry()

    def get_registry(self) -> None:
        # Prepare parameters
        registry = self.controller.management.host_registry
        accept_header = self.request.headers.get("Accept")
        accept_encoding_header = self.request.headers.get("Accept-Encoding")
        params = parse_qs(urlparse(self.request.path).query)
        # Bake output
        status, headers, output = _bake_output(
            registry, accept_header, accept_encoding_header, params, False
        )
        # Return output
        self.finish_metrics(int(status.split(" ", maxsplit=1)[0]), headers, output)

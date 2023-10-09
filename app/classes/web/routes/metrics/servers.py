from prometheus_client.exposition import _bake_output
from prometheus_client.exposition import parse_qs, urlparse

from app.classes.web.metrics_handler import BaseMetricsHandler
from app.classes.controllers.servers_controller import ServersController


# Decorate function with metric.
class ApiOpenMetricsServersHandler(BaseMetricsHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.get_registry(server_id)

    def get_registry(self, server_id=None) -> None:
        if server_id is None:
            return self.finish_json(500, {"status": "error", "error": "UNKNOWN_SERVER"})

        # Prepare parameters
        registry = (
            ServersController().get_server_instance_by_id(server_id).server_registry
        )
        accept_header = self.request.headers.get("Accept")
        accept_encoding_header = self.request.headers.get("Accept-Encoding")
        params = parse_qs(urlparse(self.request.path).query)
        # Bake output
        status, headers, output = _bake_output(
            registry, accept_header, accept_encoding_header, params, False
        )
        # Return output
        self.finish_metrics(int(status.split(" ", maxsplit=1)[0]), headers, output)

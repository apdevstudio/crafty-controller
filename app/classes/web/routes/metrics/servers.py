from prometheus_client import Histogram
from app.classes.web.metrics_handler import BaseMetricsHandler


# Decorate function with metric.
class ApiOpenMetricsServersHandler(BaseMetricsHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        self.get_registry()

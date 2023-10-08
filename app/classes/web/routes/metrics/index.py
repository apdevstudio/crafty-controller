from prometheus_client import Info
from app.classes.web.metrics_handler import BaseMetricsHandler

CRAFTY_INFO = Info("Crafty_Controller", "Infos of this Crafty Instance")


# Decorate function with metric.
class ApiOpenMetricsIndexHandler(BaseMetricsHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        version = f"{self.helper.get_version().get('major')} \
                    .{self.helper.get_version().get('minor')} \
                    .{self.helper.get_version().get('sub')}"
        CRAFTY_INFO.info(
            {"version": version, "docker": f"{self.helper.is_env_docker()}"}
        )

        self.get_registry()

import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiCraftyHostStatsHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        latest = self.controller.management.get_latest_hosts_stats()

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": latest,
            },
        )

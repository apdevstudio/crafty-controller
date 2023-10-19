import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiServersServerStatusHandler(BaseApiHandler):
    def get(self):
        servers_status = []
        servers_list = self.controller.servers.get_all_servers_stats()
        for server in servers_list:
            if server.get("server_data").get("show_status") is True:
                servers_status.append(
                    {
                        "id": server.get("server_data").get("server_id"),
                        "world_name": server.get("stats").get("world_name"),
                        "running": server.get("stats").get("running"),
                        "online": server.get("stats").get("online"),
                        "max": server.get("stats").get("max"),
                        "version": server.get("stats").get("version"),
                        "desc": server.get("stats").get("desc"),
                        "icon": server.get("stats").get("icon"),
                    }
                )

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": servers_status,
            },
        )

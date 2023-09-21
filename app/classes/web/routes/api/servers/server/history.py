import logging
from app.classes.web.base_api_handler import BaseApiHandler
from app.classes.controllers.servers_controller import ServersController


logger = logging.getLogger(__name__)


class ApiServersServerHistoryHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        srv = ServersController().get_server_instance_by_id(server_id)
        history = srv.get_server_history()

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": history,
            },
        )

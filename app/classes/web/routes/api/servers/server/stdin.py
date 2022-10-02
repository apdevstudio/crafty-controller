import logging

from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiServersServerStdinHandler(BaseApiHandler):
    def post(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.COMMANDS
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Commands permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        svr = self.controller.servers.get_server_obj_optional(server_id)
        if svr is None:
            # It's in auth_data[0] but not as a Server object
            logger.critical(
                "Something has gone VERY wrong! "
                "Crafty can't access the server object. "
                "Please report this to the devs"
            )
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if svr.send_command(self.request.body.decode("utf-8")):
            return self.finish_json(
                200,
                {"status": "ok"},
            )
        self.finish_json(
            200,
            {"status": "error", "error": "SERVER_NOT_RUNNING"},
        )

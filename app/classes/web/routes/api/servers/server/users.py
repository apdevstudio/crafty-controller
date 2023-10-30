import logging
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiServersServerUsersHandler(BaseApiHandler):
    def get(self, server_uuid: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_uuid not in [str(x["server_uuid"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if EnumPermissionsCrafty.USER_CONFIG not in auth_data[1]:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if EnumPermissionsCrafty.ROLES_CONFIG not in auth_data[1]:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": list(self.controller.servers.get_authorized_users(server_uuid)),
            },
        )

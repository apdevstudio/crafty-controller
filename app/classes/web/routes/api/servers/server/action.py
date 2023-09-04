import logging
import os
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.models.servers import Servers
from app.classes.shared.file_helpers import FileHelpers
from app.classes.shared.helpers import Helpers
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiServersServerActionHandler(BaseApiHandler):
    def post(self, server_id: str, action: str):
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

        if action == "clone_server":
            return self._clone_server(server_id, auth_data[4]["user_id"])
        if action == "eula":
            return self._agree_eula(server_id, auth_data[4]["user_id"])

        self.controller.management.send_command(
            auth_data[4]["user_id"], server_id, self.get_remote_ip(), action
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )

    def _agree_eula(self, server_id, user):
        svr = self.controller.servers.get_server_instance_by_id(server_id)
        svr.agree_eula(user)
        return self.finish_json(200, {"status": "ok"})

    def _clone_server(self, server_id, user_id):
        def is_name_used(name):
            return Servers.select().where(Servers.server_name == name).exists()

        server_data = self.controller.servers.get_server_data_by_id(server_id)
        new_server_name = server_data.get("server_name") + " (Copy)"

        name_counter = 1
        while is_name_used(new_server_name):
            name_counter += 1
            new_server_name = server_data.get("server_name") + f" (Copy {name_counter})"

        new_server_uuid = Helpers.create_uuid()
        while os.path.exists(os.path.join(self.helper.servers_dir, new_server_uuid)):
            new_server_uuid = Helpers.create_uuid()
        new_server_path = os.path.join(self.helper.servers_dir, new_server_uuid)

        self.controller.management.add_to_audit_log(
            user_id,
            f"is cloning server {server_id} named {server_data.get('server_name')}",
            server_id,
            self.get_remote_ip(),
        )

        # copy the old server
        FileHelpers.copy_dir(server_data.get("path"), new_server_path)

        # TODO get old server DB data to individual variables
        new_server_command = str(server_data.get("execution_command"))
        new_server_log_file = str(
            self.helper.get_os_understandable_path(server_data.get("log_path"))
        )

        new_server_id = self.controller.servers.create_server(
            new_server_name,
            new_server_uuid,
            new_server_path,
            "",
            new_server_command,
            server_data.get("executable"),
            new_server_log_file,
            server_data.get("stop_command"),
            server_data.get("type"),
            user_id,
            server_data.get("server_port"),
        )

        self.controller.servers.init_all_servers()

        self.finish_json(
            200,
            {"status": "ok", "data": {"new_server_id": str(new_server_id)}},
        )

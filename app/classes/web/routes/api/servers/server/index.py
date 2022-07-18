import logging
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from playhouse.shortcuts import model_to_dict
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

# TODO: modify monitoring
server_patch_schema = {
    "type": "object",
    "properties": {
        "server_name": {"type": "string", "minLength": 1},
        "path": {"type": "string", "minLength": 1},
        "backup_path": {"type": "string"},
        "executable": {"type": "string"},
        "log_path": {"type": "string", "minLength": 1},
        "execution_command": {"type": "string", "minLength": 1},
        "auto_start": {"type": "boolean"},
        "auto_start_delay": {"type": "integer"},
        "crash_detection": {"type": "boolean"},
        "stop_command": {"type": "string"},
        "executable_update_url": {"type": "string", "minLength": 1},
        "server_ip": {"type": "string", "minLength": 1},
        "server_port": {"type": "integer"},
        "logs_delete_after": {"type": "integer"},
        "type": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerIndexHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        server_obj = self.controller.servers.get_server_obj(server_id)
        server = model_to_dict(server_obj)

        # TODO: limit some columns for specific permissions?

        self.finish_json(200, {"status": "ok", "data": server})

    def patch(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, server_patch_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.CONFIG
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Config permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        server_obj = self.controller.servers.get_server_obj(server_id)
        for key in data:
            # If we don't validate the input there could be security issues
            setattr(server_obj, key, data[key])
        self.controller.servers.update_server(server_obj)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"modified the server with ID {server_id}",
            server_id,
            self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})

    def delete(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        # DELETE /api/v2/servers/server?files=true
        remove_files = self.get_query_argument("files", None) == "true"

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.CONFIG
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Config permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        logger.info(
            (
                "Removing server and all associated files for server: "
                if remove_files
                else "Removing server from panel for server: "
            )
            + self.controller.servers.get_server_friendly_name(server_id)
        )

        self.tasks_manager.remove_all_server_tasks(server_id)
        self.controller.remove_server(server_id, remove_files)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"deleted the server {server_id}",
            server_id,
            self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )

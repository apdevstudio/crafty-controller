import logging
import json
import os
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.file_helpers import FileHelpers
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

backup_patch_schema = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "minLength": 1},
        "max": {"type": "int"},
        "compress": {"type": "boolean"},
        "shutdown": {"type": "boolean"},
        "before_command": {"type": "string"},
        "after_command": {"type": "string"},
        "exclusions": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

basic_backup_patch_schema = {
    "type": "object",
    "properties": {
        "max": {"type": "int"},
        "compress": {"type": "boolean"},
        "shutdown": {"type": "boolean"},
        "before_command": {"type": "string"},
        "after_command": {"type": "string"},
        "exclusions": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerBackupsIndexHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        self.finish_json(200, self.controller.management.get_backup_config(server_id))

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
            validate(data, backup_patch_schema)
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
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.controller.management.set_backup_config(
            data["server_id"],
            data["backup_path"],
            data["max_backups"],
            data["excluded_dirs"],
            data["compress"],
            data["shutdown"],
            data["before"],
            data["after"],
        )
        return self.finish(200, {"status": "ok"})

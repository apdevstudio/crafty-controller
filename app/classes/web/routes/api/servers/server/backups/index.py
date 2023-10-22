import logging
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

backup_patch_schema = {
    "type": "object",
    "properties": {
        "backup_path": {"type": "string", "minLength": 1},
        "max_backups": {"type": "integer"},
        "compress": {"type": "boolean"},
        "shutdown": {"type": "boolean"},
        "backup_before": {"type": "string"},
        "backup_after": {"type": "string"},
        "exclusions": {"type": "array"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

basic_backup_patch_schema = {
    "type": "object",
    "properties": {
        "max_backups": {"type": "integer"},
        "compress": {"type": "boolean"},
        "shutdown": {"type": "boolean"},
        "backup_before": {"type": "string"},
        "backup_after": {"type": "string"},
        "exclusions": {"type": "array"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerBackupsIndexHandler(BaseApiHandler):
    def get(self, server_uuid: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        self.finish_json(200, self.controller.management.get_backup_config(server_uuid))

    def patch(self, server_uuid: str):
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
            if auth_data[4]["superuser"]:
                validate(data, backup_patch_schema)
            else:
                validate(data, basic_backup_patch_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        if server_uuid not in [str(x["server_uuid"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.BACKUP
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.controller.management.set_backup_config(
            server_uuid,
            data.get(
                "backup_path",
                self.controller.management.get_backup_config(server_uuid)[
                    "backup_path"
                ],
            ),
            data.get(
                "max_backups",
                self.controller.management.get_backup_config(server_uuid)[
                    "max_backups"
                ],
            ),
            data.get("exclusions"),
            data.get(
                "compress",
                self.controller.management.get_backup_config(server_uuid)["compress"],
            ),
            data.get(
                "shutdown",
                self.controller.management.get_backup_config(server_uuid)["shutdown"],
            ),
            data.get(
                "backup_before",
                self.controller.management.get_backup_config(server_uuid)["before"],
            ),
            data.get(
                "backup_after",
                self.controller.management.get_backup_config(server_uuid)["after"],
            ),
        )
        return self.finish_json(200, {"status": "ok"})

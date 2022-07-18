# TODO: read and delete

import json
import logging

from jsonschema import ValidationError, validate
from app.classes.models.management import HelpersManagement
from app.classes.models.server_permissions import EnumPermissionsServer

from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)

task_patch_schema = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean",
            "default": True,
        },
        "action": {
            "type": "string",
        },
        "interval": {"type": "integer"},
        "interval_type": {
            "type": "string",
            "enum": [
                # Basic tasks
                "hours",
                "minutes",
                "days",
                # Chain reaction tasks:
                "reaction",
                # CRON tasks:
                "",
            ],
        },
        "start_time": {"type": "string", "pattern": r"\d{1,2}:\d{1,2}"},
        "command": {"type": ["string", "null"]},
        "one_time": {"type": "boolean", "default": False},
        "cron_string": {"type": "string", "default": ""},
        "parent": {"type": ["integer", "null"]},
        "delay": {"type": "integer", "default": 0},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerTasksTaskIndexHandler(BaseApiHandler):
    def get(self, server_id: str, task_id: str):
        pass

    def delete(self, server_id: str, task_id: str):
        pass

    def patch(self, server_id: str, task_id: str):
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
            validate(data, task_patch_schema)
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
            EnumPermissionsServer.SCHEDULE
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        # Checks to make sure some doofus didn't actually make the newly
        # created task a child of itself.
        if str(data.get("parent")) == str(task_id) and data.get("parent") is not None:
            data["parent"] = None

        HelpersManagement.update_scheduled_task(task_id, data)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_id}: updated schedule",
            server_id,
            self.get_remote_ip(),
        )
        self.tasks_manager.reload_schedule_from_db()

        self.finish_json(200, {"status": "ok"})

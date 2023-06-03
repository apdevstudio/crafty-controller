# TODO: read and delete

import json
import logging

from croniter import croniter
from jsonschema import ValidationError, validate
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.webhook_handler import WebhookHandler

from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)

task_patch_schema = {
    "type": "object",
    "properties": {
        "webhook_type": {"type": "string", "enum": WebhookHandler.get_providers()},
        "name": {"type": "string"},
        "url": {"type": "string"},
        "bot_name": {"type": "string"},
        "trigger": {"type": "array"},
        "body": {"type": "string"},
        "enabled": {
            "type": "boolean",
            "default": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerWebhooksWebhookIndexHandler(BaseApiHandler):
    def get(self, server_id: str, webhook_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.CONFIG
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        if (
            not str(webhook_id)
            in self.controller.management.get_webhooks_by_server(server_id).keys()
        ):
            return self.finish_json(
                400, {"status": "error", "error": "NO WEBHOOK FOUND"}
            )
        self.finish_json(200, self.controller.management.get_webhook_by_id(webhook_id))

    def delete(self, server_id: str, webhook_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.CONFIG
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            self.controller.management.delete_webhook(webhook_id)
        except Exception:
            return self.finish_json(
                400, {"status": "error", "error": "NO WEBHOOK FOUND"}
            )
        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_id}: removed webhook",
            server_id,
            self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})

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

        data["server_id"] = server_id
        if data["cron_string"] != "" and not croniter.is_valid(data["cron_string"]):
            return self.finish_json(
                405,
                {
                    "status": "error",
                    "error": self.helper.translation.translate(
                        "error",
                        "cronFormat",
                        self.controller.users.get_user_lang_by_id(
                            auth_data[4]["user_id"]
                        ),
                    ),
                },
            )
        self.tasks_manager.update_job(task_id, data)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_id}: updated schedule",
            server_id,
            self.get_remote_ip(),
        )
        self.tasks_manager.reload_schedule_from_db()

        self.finish_json(200, {"status": "ok"})

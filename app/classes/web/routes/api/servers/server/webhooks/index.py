# TODO: create and read

import json
import logging

from jsonschema import ValidationError, validate
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.base_api_handler import BaseApiHandler
from app.classes.web.webhooks.webhook_factory import WebhookFactory


logger = logging.getLogger(__name__)
new_webhook_schema = {
    "type": "object",
    "properties": {
        "webhook_type": {
            "type": "string",
            "enum": WebhookFactory.get_supported_providers(),
        },
        "name": {"type": "string"},
        "url": {"type": "string"},
        "bot_name": {"type": "string"},
        "trigger": {"type": "array"},
        "body": {"type": "string"},
        "color": {"type": "string", "default": "#005cd1"},
        "enabled": {
            "type": "boolean",
            "default": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 7,
}


class ApiServersServerWebhooksIndexHandler(BaseApiHandler):
    def get(self, server_uuid: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if (
            EnumPermissionsServer.CONFIG
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": self.controller.management.get_webhooks_by_server(server_uuid),
            },
        )

    def post(self, server_uuid: str):
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
            validate(data, new_webhook_schema)
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
            EnumPermissionsServer.CONFIG
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_uuid
            )
        ):
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        data["server_uuid"] = server_uuid

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_uuid}: added webhook",
            server_uuid,
            self.get_remote_ip(),
        )
        triggers = ""
        for item in data["trigger"]:
            string = item + ","
            triggers += string
        data["trigger"] = triggers
        webhook_id = self.controller.management.create_webhook(data)

        self.finish_json(200, {"status": "ok", "data": {"webhook_id": webhook_id}})

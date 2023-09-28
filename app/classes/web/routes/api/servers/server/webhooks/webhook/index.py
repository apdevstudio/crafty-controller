# TODO: read and delete

import json
import logging

from jsonschema import ValidationError, validate
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.webhooks.webhook_factory import WebhookFactory
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)

webhook_patch_schema = {
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
        "enabled": {
            "type": "boolean",
            "default": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerWebhooksManagementIndexHandler(BaseApiHandler):
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
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": self.controller.management.get_webhook_by_id(webhook_id),
            },
        )

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

    def patch(self, server_id: str, webhook_id: str):
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
            validate(data, webhook_patch_schema)
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
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        data["server_id"] = server_id
        if "trigger" in data.keys():
            triggers = ""
            for item in data["trigger"]:
                string = item + ","
                triggers += string
            data["trigger"] = triggers
        self.controller.management.modify_webhook(webhook_id, data)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_id}: updated webhook",
            server_id,
            self.get_remote_ip(),
        )

        self.finish_json(200, {"status": "ok"})

    def post(self, server_id: str, webhook_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            "Tested webhook",
            server_id,
            self.get_remote_ip(),
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
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        webhook = self.controller.management.get_webhook_by_id(webhook_id)
        try:
            webhook_provider = WebhookFactory.create_provider(webhook["webhook_type"])
            webhook_provider.send(
                server_name=server_id,  # TODO get actual server name
                title="Tickle Test Webhook",
                url=webhook["url"],
                message=webhook["body"],
                color=4915409,  # Prestigious purple!
            )
        except Exception as e:
            self.finish_json(500, {"status": "error", "error": str(e)})

        self.finish_json(200, {"status": "ok"})

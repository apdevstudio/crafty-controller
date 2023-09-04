import json
import logging

from jsonschema import ValidationError, validate
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiUsersUserKeyHandler(BaseApiHandler):
    def get(self, user_id: str, key_id=None):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        if key_id:
            key = self.controller.users.get_user_api_key(key_id)
            # does this user id exist?
            if key is None:
                self.redirect("/panel/error?error=Invalid Key ID")
                return

            if (
                str(key.user_id) != str(auth_data[4]["user_id"])
                and not auth_data[4]["superuser"]
            ):
                return self.finish_json(
                    400,
                    {
                        "status": "error",
                        "error": "NOT AUTHORIZED",
                        "error_data": "TRIED TO EDIT KEY WIHTOUT AUTH",
                    },
                )

            self.controller.management.add_to_audit_log(
                auth_data[4]["user_id"],
                f"Generated a new API token for the key {key.name} "
                f"from user with UID: {key.user_id}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            data_key = self.controller.authentication.generate(
                key.user_id_id, {"token_id": key.token_id}
            )

            return self.finish_json(
                200,
                {"status": "ok", "data": data_key},
            )
        else:
            if (
                str(user_id) != str(auth_data[4]["user_id"])
                and not auth_data[4]["superuser"]
            ):
                return self.finish_json(
                    400,
                    {
                        "status": "error",
                        "error": "NOT AUTHORIZED",
                        "error_data": "TRIED TO EDIT KEY WIHTOUT AUTH",
                    },
                )
            keys = []
            for key in self.controller.users.get_user_api_keys(str(user_id)):
                keys.append(
                    {
                        "id": key.token_id,
                        "name": key.name,
                        "server_permissions": key.server_permissions,
                        "crafty_permissions": key.crafty_permissions,
                        "superuser": key.superuser,
                    }
                )
            self.finish_json(
                200,
                {
                    "status": "ok",
                    "data": keys,
                },
            )

    def patch(self, user_id: str):
        user_key_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 3},
                "server_permissions_mask": {
                    "type": "string",
                    "pattern": "^[01]{8}$",  # 8 bits, see EnumPermissionsServer
                },
                "crafty_permissions_mask": {
                    "type": "string",
                    "pattern": "^[01]{3}$",  # 8 bits, see EnumPermissionsCrafty
                },
                "superuser": {"type": "boolean"},
            },
            "additionalProperties": False,
            "minProperties": 1,
        }
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _exec_user_crafty_permissions,
            _,
            _superuser,
            user,
        ) = auth_data

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, user_key_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        if user_id == "@me":
            user_id = user["user_id"]
        # does this user id exist?
        if not self.controller.users.user_id_exists(user_id):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "USER NOT FOUND",
                    "error_data": "USER_NOT_FOUND",
                },
            )

        if (
            str(user_id) != str(auth_data[4]["user_id"])
            and not auth_data[4]["superuser"]
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT AUTHORIZED",
                    "error_data": "TRIED TO EDIT KEY WIHTOUT AUTH",
                },
            )

        key_id = self.controller.users.add_user_api_key(
            data["name"],
            user_id,
            data["superuser"],
            data["server_permissions_mask"],
            data["crafty_permissions_mask"],
        )

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Added API key {data['name']} with crafty permissions "
            f"{data['crafty_permissions_mask']}"
            f" and {data['server_permissions_mask']} for user with UID: {user_id}",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )
        self.finish_json(200, {"status": "ok", "data": {"id": key_id}})

    def delete(self, _user_id: str, key_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _exec_user_crafty_permissions,
            _,
            _,
            _user,
        ) = auth_data
        if key_id:
            key = self.controller.users.get_user_api_key(key_id)
            # does this user id exist?
            if key is None:
                self.redirect("/panel/error?error=Invalid Key ID")
                return

            # does this user id exist?
            target_key = self.controller.users.get_user_api_key(key_id)
            if not target_key:
                return self.finish_json(
                    400,
                    {
                        "status": "error",
                        "error": "INVALID KEY",
                        "error_data": "INVALID KEY ID",
                    },
                )

            if (
                target_key.user_id != auth_data[4]["user_id"]
                and not auth_data[4]["superuser"]
            ):
                return self.finish_json(
                    400,
                    {
                        "status": "error",
                        "error": "NOT AUTHORIZED",
                        "error_data": "TRIED TO EDIT KEY WIHTOUT AUTH",
                    },
                )

            self.controller.users.delete_user_api_key(key_id)

            self.controller.management.add_to_audit_log(
                auth_data[4]["user_id"],
                f"Removed API key {target_key} "
                f"(ID: {key_id}) from user {auth_data[4]['user_id']}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )

            return self.finish_json(
                200,
                {"status": "ok", "data": {"id": key_id}},
            )

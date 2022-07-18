from jsonschema import ValidationError, validate
import orjson
from peewee import DoesNotExist
from app.classes.web.base_api_handler import BaseApiHandler

modify_role_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
        },
        "servers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "permissions": {
                        "type": "string",
                        "pattern": "^[01]{8}$",  # 8 bits, see EnumPermissionsServer
                    },
                },
                "required": ["server_id", "permissions"],
            },
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiRolesRoleIndexHandler(BaseApiHandler):
    def get(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            _,
        ) = auth_data

        if not superuser:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            self.finish_json(
                200,
                {"status": "ok", "data": self.controller.roles.get_role(role_id)},
            )
        except DoesNotExist:
            self.finish_json(404, {"status": "error", "error": "ROLE_NOT_FOUND"})

    def delete(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            user,
        ) = auth_data

        if not superuser:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.controller.roles.remove_role(role_id)

        self.finish_json(
            200,
            {"status": "ok", "data": role_id},
        )

        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"deleted role with ID {role_id}",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

    def patch(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            user,
        ) = auth_data

        if not superuser:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = orjson.loads(self.request.body)
        except orjson.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, modify_role_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        try:
            self.controller.roles.update_role_advanced(
                role_id, data.get("role_name", None), data.get("servers", None)
            )
        except DoesNotExist:
            return self.finish_json(404, {"status": "error", "error": "ROLE_NOT_FOUND"})

        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"modified role with ID {role_id}",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )

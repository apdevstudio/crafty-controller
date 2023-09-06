import typing as t
from jsonschema import ValidationError, validate
import orjson
from playhouse.shortcuts import model_to_dict
from app.classes.web.base_api_handler import BaseApiHandler

create_role_schema = {
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
        "manager": {"type": ["integer", "null"]},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

basic_create_role_schema = {
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


class ApiRolesIndexHandler(BaseApiHandler):
    def get(self):
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

        # GET /api/v2/roles?ids=true
        get_only_ids = self.get_query_argument("ids", None) == "true"

        if not superuser:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": self.controller.roles.get_all_role_ids()
                if get_only_ids
                else [model_to_dict(r) for r in self.controller.roles.get_all_roles()],
            },
        )

    def post(self):
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
            if auth_data[4]["superuser"]:
                validate(data, create_role_schema)
            else:
                validate(data, basic_create_role_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        role_name = data["name"]
        manager = data.get("manager", None)
        if manager == self.controller.users.get_id_by_name("SYSTEM") or manager == 0:
            manager = None

        # Get the servers
        servers_dict = {server["server_id"]: server for server in data["servers"]}
        server_ids = (
            (
                {server["server_id"] for server in data["servers"]}
                & set(self.controller.servers.get_all_server_ids())
            )  # Only allow existing servers
            if "servers" in data
            else set()
        )
        servers: t.List[dict] = [servers_dict[server_id] for server_id in server_ids]

        if self.controller.roles.get_roleid_by_name(role_name) is not None:
            return self.finish_json(
                400, {"status": "error", "error": "ROLE_NAME_ALREADY_EXISTS"}
            )

        role_id = self.controller.roles.add_role_advanced(role_name, servers, manager)

        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"created role {role_name} (RID:{role_id})",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok", "data": {"role_id": role_id}},
        )

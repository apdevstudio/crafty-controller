import typing as t
from app.classes.web.base_api_handler import BaseApiHandler
from app.classes.web.routes.api.auth.login import login_schema
from app.classes.web.routes.api.roles.role.index import modify_role_schema
from app.classes.web.routes.api.roles.index import create_role_schema
from app.classes.web.routes.api.servers.server.index import server_patch_schema
from app.classes.web.routes.api.servers.index import new_server_schema
from app.classes.web.routes.api.servers.server.tasks.task.index import task_patch_schema

SCHEMA_LIST: t.Final = [
    "login",
    "modify_role",
    "create_role",
    "server_patch",
    "new_server",
    "user_patch",
    "new_user",
    "task_patch",
]


class ApiJsonSchemaListHandler(BaseApiHandler):
    def get(self):
        self.finish_json(
            200,
            {"status": "ok", "data": SCHEMA_LIST},
        )


class ApiJsonSchemaHandler(BaseApiHandler):
    def get(self, schema_name: str):
        if schema_name == "login":
            self.finish_json(
                200,
                {"status": "ok", "data": login_schema},
            )
        elif schema_name == "modify_role":
            self.finish_json(
                200,
                {"status": "ok", "data": modify_role_schema},
            )
        elif schema_name == "create_role":
            self.finish_json(
                200,
                {"status": "ok", "data": create_role_schema},
            )
        elif schema_name == "server_patch":
            self.finish_json(200, {"status": "ok", "data": server_patch_schema})
        elif schema_name == "new_server":
            self.finish_json(
                200,
                {"status": "ok", "data": new_server_schema},
            )
        elif schema_name == "user_patch":
            self.finish_json(
                200,
                {
                    "status": "ok",
                    "data": {
                        "type": "object",
                        "properties": {
                            **self.controller.users.user_jsonschema_props,
                        },
                        "additionalProperties": False,
                        "minProperties": 1,
                    },
                },
            )
        elif schema_name == "new_user":
            self.finish_json(
                200,
                {
                    "status": "ok",
                    "data": {
                        "type": "object",
                        "properties": {
                            **self.controller.users.user_jsonschema_props,
                        },
                        "required": ["username", "password"],
                        "additionalProperties": False,
                    },
                },
            )
        elif schema_name == "task_patch":
            self.finish_json(
                200,
                {"status": "ok", "data": task_patch_schema},
            )
        else:
            self.finish_json(
                404,
                {
                    "status": "error",
                    "error": "UNKNOWN_JSON_SCHEMA",
                    "info": (
                        f"Unknown JSON schema: {schema_name}."
                        f" Here's a list of all the valid schema names: {SCHEMA_LIST}"
                    ),
                },
            )

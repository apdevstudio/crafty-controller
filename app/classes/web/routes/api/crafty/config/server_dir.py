from jsonschema import ValidationError, validate
import orjson
from playhouse.shortcuts import model_to_dict
from app.classes.web.base_api_handler import BaseApiHandler

server_dir_schema = {
    "type": "object",
    "properties": {
        "new_dir": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiCraftyConfigServerDirHandler(BaseApiHandler):
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

    def patch(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            _,
            _,
        ) = auth_data

        if not auth_data:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if not auth_data[4]["superuser"]:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        if self.helper.is_env_docker():
            raise NotImplementedError

        try:
            data = orjson.loads(self.request.body)
        except orjson.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, server_dir_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        if self.helper.dir_migration:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "IN PROGRESS",
                    "error_data": "Migration already in progress. Please be patient",
                },
            )
        for server in self.controller.servers.get_all_servers_stats():
            if server["stats"]["running"]:
                return self.finish_json(
                    400,
                    {
                        "status": "error",
                        "error": "SERVER RUNNING",
                    },
                )

        new_dir = data["new_dir"]
        self.controller.update_master_server_dir(new_dir, auth_data[4]["user_id"])

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"updated master servers dir to {new_dir}/servers",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )

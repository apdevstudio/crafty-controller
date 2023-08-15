from jsonschema import ValidationError, validate
import orjson
from playhouse.shortcuts import model_to_dict
from app.classes.web.base_api_handler import BaseApiHandler

config_json_schema = {
    "type": "object",
    "properties": {
        "http_port": {"type": "integer"},
        "https_port": {"type": "integer"},
        "language": {
            "type": "string",
        },
        "cookie_expire": {"type": "integer"},
        "show_errors": {"type": "boolean"},
        "history_max_age": {"type": "integer"},
        "stats_update_frequency_seconds": {"type": "integer"},
        "delete_default_json": {"type": "boolean"},
        "show_contribute_link": {"type": "boolean"},
        "virtual_terminal_lines": {"type": "integer"},
        "max_log_lines": {"type": "integer"},
        "max_audit_entries": {"type": "integer"},
        "disabled_language_files": {"type": "array"},
        "stream_size_GB": {"type": "integer"},
        "keywords": {"type": "string"},
        "allow_nsfw_profile_pictures": {"type": "boolean"},
        "enable_user_self_delete": {"type": "boolean"},
        "reset_secrets_on_next_boot": {"type": "boolean"},
        "monitored_mounts": {"type": "array"},
        "dir_size_poll_freq_minutes": {"type": "integer"},
        "crafty_logs_delete_after_days": {"type": "integer"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiCraftyConfigIndexHandler(BaseApiHandler):
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
            validate(data, config_json_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        self.controller.set_config_json(data)

        self.controller.management.add_to_audit_log(
            user["user_id"],
            "edited config.json",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )

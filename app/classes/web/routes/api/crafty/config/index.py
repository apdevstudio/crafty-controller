import os
import json
from jsonschema import ValidationError, validate
import orjson
from playhouse.shortcuts import model_to_dict
from app.classes.shared.file_helpers import FileHelpers
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
        "keywords": {"type": "array"},
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
customize_json_schema = {
    "type": "object",
    "properties": {
        "photo": {"type": "string"},
        "opacity": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

photo_delete_schema = {
    "type": "object",
    "properties": {
        "photo": {"type": "string"},
    },
    "additionalProperties": False,
    "minProperties": 1,
}
default_photo = "login_1.jpg"


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


class ApiCraftyCustomizeIndexHandler(BaseApiHandler):
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
            validate(data, customize_json_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        if not self.helper.validate_traversal(
            os.path.join(
                self.controller.project_root,
                "app/frontend/static/assets/images/auth/",
            ),
            os.path.join(
                self.controller.project_root,
                f"app/frontend/static/assets/images/auth/{data['photo']}",
            ),
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": "TRIED TO REACH FILES THAT ARE"
                    " NOT SUPPOSED TO BE ACCESSIBLE",
                },
            )
        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"customized login photo: {data['photo']}/{data['opacity']}",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )
        self.controller.management.set_login_opacity(int(data["opacity"]))
        if data["photo"] == default_photo:
            self.controller.management.set_login_image(default_photo)
            self.controller.cached_login = f"{data['photo']}"
        else:
            self.controller.management.set_login_image(f"custom/{data['photo']}")
            self.controller.cached_login = f"custom/{data['photo']}"
        self.finish_json(
            200,
            {
                "status": "ok",
                "data": {"photo": data["photo"], "opacity": data["opacity"]},
            },
        )

    def delete(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if not auth_data[4]["superuser"]:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        try:
            validate(data, photo_delete_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        if not self.helper.validate_traversal(
            os.path.join(
                self.controller.project_root,
                "app",
                "frontend",
                "/static/assets/images/auth/",
            ),
            os.path.join(
                self.controller.project_root,
                "app",
                "frontend",
                "/static/assets/images/auth/",
                data["photo"],
            ),
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "TRAVERSAL DETECTED",
                    "error_data": "TRIED TO REACH FILES THAT ARE"
                    " NOT SUPPOSED TO BE ACCESSIBLE",
                },
            )
        if data["photo"] == default_photo:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID FILE",
                    "error_data": "CANNOT DELETE DEFAULT",
                },
            )
        FileHelpers.del_file(
            os.path.join(
                self.controller.project_root,
                f"app/frontend/static/assets/images/auth/custom/{data['photo']}",
            )
        )
        current = self.controller.cached_login
        split = current.split("/")
        if len(split) == 1:
            current_photo = current
        else:
            current_photo = split[1]
        if current_photo == data["photo"]:
            self.controller.management.set_login_image(default_photo)
            self.controller.cached_login = default_photo
        return self.finish_json(200, {"status": "ok"})

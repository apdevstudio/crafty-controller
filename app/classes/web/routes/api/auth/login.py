import logging
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.users import Users
from app.classes.shared.helpers import Helpers
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)
auth_log = logging.getLogger("auth")
login_schema = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "maxLength": 20,
            "minLength": 4,
            "pattern": "^[a-z0-9_]+$",
        },
        "password": {"type": "string", "maxLength": 20, "minLength": 4},
    },
    "required": ["username", "password"],
    "additionalProperties": False,
}


class ApiAuthLoginHandler(BaseApiHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            logger.error(
                "Invalid JSON schema for API"
                f" login attempt from {self.get_remote_ip()}"
            )
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, login_schema)
        except ValidationError as e:
            logger.error(
                "Invalid JSON schema for API"
                f" login attempt from {self.get_remote_ip()}"
            )
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        username = data["username"]
        password = data["password"]

        # pylint: disable=no-member
        user_data = Users.get_or_none(Users.username == username)

        if user_data is None:
            self.controller.log_attempt(self.get_remote_ip(), username)
            auth_log.error(
                f"User attempted to log into {username}."
                " Authentication failed from remote IP"
                f" {self.get_remote_ip()}. User not found"
            )
            return self.finish_json(
                401,
                {"status": "error", "error": "INCORRECT_CREDENTIALS", "token": None},
            )

        if not user_data.enabled:
            auth_log.error(
                f"User attempted to log into {username}."
                " Authentication failed from remote"
                f" IP {self.get_remote_ip()} account disabled"
            )
            self.finish_json(
                403, {"status": "error", "error": "ACCOUNT_DISABLED", "token": None}
            )
            return

        login_result = self.helper.verify_pass(password, user_data.password)

        # Valid Login
        if login_result:
            auth_log.info(
                f"{username} successfully"
                " authenticated and logged"
                f" into panel from remote IP {self.get_remote_ip()}"
            )
            logger.info(f"User: {user_data} Logged in from IP: {self.get_remote_ip()}")

            # record this login
            query = Users.select().where(Users.username == username.lower()).get()
            query.last_ip = self.get_remote_ip()
            query.last_login = Helpers.get_time_as_string()
            query.save()

            # log this login
            self.controller.management.add_to_audit_log(
                user_data.user_id, "logged in via the API", 0, self.get_remote_ip()
            )

            self.finish_json(
                200,
                {
                    "status": "ok",
                    "data": {
                        "token": self.controller.authentication.generate(
                            user_data.user_id
                        ),
                        "user_id": str(user_data.user_id),
                    },
                },
            )
        else:
            # log this failed login attempt
            self.controller.management.add_to_audit_log(
                user_data.user_id, "Tried to log in", 0, self.get_remote_ip()
            )
            self.finish_json(
                401,
                {"status": "error", "error": "INCORRECT_CREDENTIALS"},
            )

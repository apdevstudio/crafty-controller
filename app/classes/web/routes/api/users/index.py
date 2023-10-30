import logging
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.models.roles import Roles, HelperRoles
from app.classes.models.users import PUBLIC_USER_ATTRS
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiUsersIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_crafty_permissions,
            _,
            _,
            user,
        ) = auth_data

        # GET /api/v2/users?ids=true
        get_only_ids = self.get_query_argument("ids", None) == "true"

        if EnumPermissionsCrafty.USER_CONFIG in exec_user_crafty_permissions:
            if get_only_ids:
                data = self.controller.users.get_all_user_ids()
            else:
                data = [
                    {key: getattr(user_res, key) for key in PUBLIC_USER_ATTRS}
                    for user_res in self.controller.users.get_all_users().execute()
                ]
        else:
            if get_only_ids:
                data = [user["user_id"]]
            else:
                user_res = self.controller.users.get_user_by_id(user["user_id"])
                user_res["roles"] = list(
                    map(HelperRoles.get_role, user_res.get("roles", set()))
                )
                data = [{key: user_res[key] for key in PUBLIC_USER_ATTRS}]

        self.finish_json(
            200,
            {
                "status": "ok",
                "data": data,
            },
        )

    def post(self):
        new_user_schema = {
            "type": "object",
            "properties": {
                **self.controller.users.user_jsonschema_props,
            },
            "required": ["username", "password"],
            "additionalProperties": False,
        }
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_crafty_permissions,
            _,
            superuser,
            user,
        ) = auth_data

        if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, new_user_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        username = data["username"]
        username = str(username).lower()
        manager = data.get("manager", None)
        if user["superuser"]:
            if (
                manager == self.controller.users.get_id_by_name("SYSTEM")
                or manager == 0
            ):
                manager = None
        else:
            manager = int(user["user_id"])
        password = data["password"]
        email = data.get("email", "default@example.com")
        enabled = data.get("enabled", True)
        lang = data.get("lang", self.helper.get_setting("language"))
        new_superuser = data.get("superuser", False)
        permissions = data.get("permissions", None)
        roles = data.get("roles", None)
        hints = data.get("hints", True)
        theme = data.get("theme", "default")

        if username.lower() in ["system", ""]:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_USERNAME"}
            )

        if self.controller.users.get_id_by_name(username) is not None:
            return self.finish_json(400, {"status": "error", "error": "USER_EXISTS"})

        if roles is None:
            roles = set()
        else:
            role_ids = [str(role_id) for role_id in Roles.select(Roles.role_id)]
            roles = {role for role in roles if str(role) in role_ids}

        permissions_mask = "0" * len(EnumPermissionsCrafty.__members__.items())
        server_quantity = {
            perm.name: 0
            for perm in self.controller.crafty_perms.list_defined_crafty_permissions()
        }

        if permissions is not None:
            server_quantity = {}
            permissions_mask = list(permissions_mask)
            for permission in permissions:
                server_quantity[permission["name"]] = permission["quantity"]
                permissions_mask[EnumPermissionsCrafty[permission["name"]].value] = (
                    "1" if permission["enabled"] else "0"
                )
            permissions_mask = "".join(permissions_mask)

        if new_superuser and not superuser:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_SUPERUSER_CREATE"}
            )

        if len(roles) != 0 and not superuser:
            # HACK: This should check if the user has the roles or something
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_ROLES_CREATE"}
            )

        # TODO: do this in the most efficient way
        user_id = self.controller.users.add_user(
            username,
            manager,
            password,
            email,
            enabled,
            new_superuser,
            theme,
        )
        self.controller.users.update_user(
            user_id,
            {"roles": roles, "lang": lang, "hints": hints},
            {
                "permissions_mask": permissions_mask,
                "server_quantity": server_quantity,
            },
        )

        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"added user {username} (UID:{user_id}) with roles {roles}",
            server_uuid=0,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            201,
            {"status": "ok", "data": {"user_id": str(user_id)}},
        )

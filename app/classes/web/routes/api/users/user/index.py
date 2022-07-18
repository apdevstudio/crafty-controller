import json
import logging
import typing as t

from jsonschema import ValidationError, validate
from app.classes.controllers.users_controller import UsersController
from app.classes.models.crafty_permissions import (
    EnumPermissionsCrafty,
    PermissionsCrafty,
)
from app.classes.models.roles import HelperRoles
from app.classes.models.users import HelperUsers
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiUsersUserIndexHandler(BaseApiHandler):
    def get(self, user_id: str):
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

        if user_id in ["@me", user["user_id"]]:
            user_id = user["user_id"]
            res_user = user
        elif EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                },
            )
        else:
            # has User_Config permission and isn't viewing self
            res_user = self.controller.users.get_user_by_id(user_id)
            if not res_user:
                return self.finish_json(
                    404,
                    {
                        "status": "error",
                        "error": "USER_NOT_FOUND",
                    },
                )

        # Remove password and valid_tokens_from from the response
        # as those should never be sent out to the client.
        res_user.pop("password", None)
        res_user.pop("valid_tokens_from", None)
        res_user["roles"] = list(
            map(HelperRoles.get_role, res_user.get("roles", set()))
        )

        self.finish_json(
            200,
            {"status": "ok", "data": res_user},
        )

    def delete(self, user_id: str):
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

        if (user_id in ["@me", user["user_id"]]) and self.helper.get_setting(
            "allow_self_delete", False
        ):
            user_id = user["user_id"]
            self.controller.users.remove_user(user_id)
        elif EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                },
            )
        else:
            # has User_Config permission
            self.controller.users.remove_user(user_id)

        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"deleted the user {user_id}",
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )

    def patch(self, user_id: str):
        user_patch_schema = {
            "type": "object",
            "properties": {
                **self.controller.users.user_jsonschema_props,
            },
            "additionalProperties": False,
            "minProperties": 1,
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

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, user_patch_schema)
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

        if (
            EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions
            and str(user["user_id"]) != str(user_id)
        ):
            # If doesn't have perm can't edit other users
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                },
            )

        if "username" in data:
            if data["username"].lower() in ["system", ""]:
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_USERNAME"}
                )
            if self.controller.users.get_id_by_name(data["username"]) is not None:
                return self.finish_json(
                    400, {"status": "error", "error": "USER_EXISTS"}
                )

        if "superuser" in data:
            if str(user["user_id"]) == str(user_id) and not superuser:
                # Checks if user is trying to change super user status
                # of self without superuser. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_SUPERUSER_MODIFY"}
                )
            if not superuser:
                # The user is not superuser so they can't change the superuser status
                data.pop("superuser")

        if "permissions" in data:
            if str(user["user_id"]) == str(user_id) and not superuser:
                # Checks if user is trying to change permissions
                # of self without superuser. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_PERMISSIONS_MODIFY"}
                )
            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                # Checks if user is trying to change permissions of someone
                # else without User Config permission. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_PERMISSIONS_MODIFY"}
                )

        if "roles" in data:
            if str(user["user_id"]) == str(user_id) and not superuser:
                # Checks if user is trying to change roles of
                # self without superuser. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_ROLES_MODIFY"}
                )
            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                # Checks if user is trying to change roles of someone
                # else without User Config permission. We don't want that.
                return self.finish_json(
                    400, {"status": "error", "error": "INVALID_ROLES_MODIFY"}
                )

        if "password" in data and str(user["user_id"] == str(user_id)):
            # TODO: edit your own password
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_PASSWORD_MODIFY"}
            )

        user_obj = HelperUsers.get_user_model(user_id)

        if "roles" in data:
            roles: t.Set[str] = set(data.pop("roles"))
            base_roles: t.Set[str] = set(user_obj.roles)
            added_roles = roles.difference(base_roles)
            removed_roles = base_roles.difference(roles)
            logger.debug(
                f"updating user {user_id}'s roles: "
                f"+role:{added_roles} -role:{removed_roles}"
            )

            for role_id in added_roles:
                HelperUsers.get_or_create(user_id, role_id)

            if len(removed_roles) != 0:
                self.controller.users.users_helper.delete_user_roles(
                    user_id, removed_roles
                )

        if "permissions" in data:
            permissions: t.List[UsersController.ApiPermissionDict] = data.pop(
                "permissions"
            )
            permissions_mask = "0" * len(EnumPermissionsCrafty)
            limit_server_creation = 0
            limit_user_creation = 0
            limit_role_creation = 0

            for permission in permissions:
                self.controller.crafty_perms.set_permission(
                    permissions_mask,
                    EnumPermissionsCrafty.__members__[permission["name"]],
                    "1" if permission["enabled"] else "0",
                )

            PermissionsCrafty.add_or_update_user(
                user_id,
                permissions_mask,
                limit_server_creation,
                limit_user_creation,
                limit_role_creation,
            )

        # TODO: make this more efficient
        if len(data) != 0:
            for key in data:
                # If we don't validate the input there could be security issues
                value = data[key]
                if key == "password":
                    value = self.helper.encode_pass(value)
                setattr(user_obj, key, value)
            user_obj.save()

        self.controller.management.add_to_audit_log(
            user["user_id"],
            (
                f"edited user {user_obj.username} (UID: {user_id})"
                f"with roles {user_obj.roles}"
            ),
            server_id=0,
            source_ip=self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})

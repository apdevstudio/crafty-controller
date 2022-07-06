import logging
import typing as t

from app.classes.models.users import HelperUsers
from app.classes.models.crafty_permissions import (
    PermissionsCrafty,
    EnumPermissionsCrafty,
)

logger = logging.getLogger(__name__)


class UsersController:
    class ApiPermissionDict(t.TypedDict):
        name: str
        quantity: int
        enabled: bool

    def __init__(self, helper, users_helper, authentication):
        self.helper = helper
        self.users_helper = users_helper
        self.authentication = authentication

        _permissions_props = {
            "name": {
                "type": "string",
                "enum": [
                    permission.name
                    for permission in PermissionsCrafty.get_permissions_list()
                ],
            },
            "quantity": {"type": "number", "minimum": 0},
            "enabled": {"type": "boolean"},
        }
        self.user_jsonschema_props: t.Final = {
            "username": {
                "type": "string",
                "maxLength": 20,
                "minLength": 4,
                "pattern": "^[a-z0-9_]+$",
                "examples": ["admin"],
                "title": "Username",
            },
            "password": {
                "type": "string",
                "maxLength": 20,
                "minLength": 4,
                "examples": ["crafty"],
                "title": "Password",
            },
            "email": {
                "type": "string",
                "format": "email",
                "examples": ["default@example.com"],
                "title": "E-Mail",
            },
            "enabled": {
                "type": "boolean",
                "examples": [True],
                "title": "Enabled",
            },
            "lang": {
                "type": "string",
                "maxLength": 10,
                "minLength": 2,
                "examples": ["en"],
                "title": "Language",
            },
            "superuser": {
                "type": "boolean",
                "examples": [False],
                "title": "Superuser",
            },
            "permissions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": _permissions_props,
                    "required": ["name", "quantity", "enabled"],
                },
            },
            "roles": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1,
                },
            },
            "hints": {"type": "boolean"},
        }

    # **********************************************************************************
    #                                   Users Methods
    # **********************************************************************************
    @staticmethod
    def get_all_users():
        return HelperUsers.get_all_users()

    @staticmethod
    def get_all_user_ids() -> t.List[int]:
        return HelperUsers.get_all_user_ids()

    @staticmethod
    def get_all_usernames():
        return HelperUsers.get_all_usernames()

    @staticmethod
    def get_id_by_name(username):
        return HelperUsers.get_user_id_by_name(username)

    @staticmethod
    def get_user_lang_by_id(user_id):
        return HelperUsers.get_user_lang_by_id(user_id)

    @staticmethod
    def get_user_by_id(user_id):
        return HelperUsers.get_user(user_id)

    @staticmethod
    def update_server_order(user_id, user_server_order):
        HelperUsers.update_server_order(user_id, user_server_order)

    @staticmethod
    def get_server_order(user_id):
        return HelperUsers.get_server_order(user_id)

    @staticmethod
    def user_query(user_id):
        return HelperUsers.user_query(user_id)

    @staticmethod
    def set_support_path(user_id, support_path):
        HelperUsers.set_support_path(user_id, support_path)

    def update_user(self, user_id: str, user_data=None, user_crafty_data=None):
        if user_crafty_data is None:
            user_crafty_data = {}
        if user_data is None:
            user_data = {}
        base_data = HelperUsers.get_user(user_id)
        up_data = {}
        added_roles = set()
        removed_roles = set()
        for key in user_data:
            if key == "user_id":
                continue
            if key == "roles":
                added_roles = set(user_data["roles"]).difference(
                    set(base_data["roles"])
                )
                removed_roles = set(base_data["roles"]).difference(
                    set(user_data["roles"])
                )
            elif key == "password":
                if user_data["password"] is not None and user_data["password"] != "":
                    up_data["password"] = self.helper.encode_pass(user_data["password"])
            elif key == "lang":
                up_data["lang"] = user_data["lang"]
            elif key == "hints":
                up_data["hints"] = user_data["hints"]
            elif base_data[key] != user_data[key]:
                up_data[key] = user_data[key]
        up_data["last_update"] = self.helper.get_time_as_string()
        logger.debug(f"user: {user_data} +role:{added_roles} -role:{removed_roles}")
        for role in added_roles:
            HelperUsers.get_or_create(user_id=user_id, role_id=role)
        permissions_mask = user_crafty_data.get("permissions_mask", "000")

        if "server_quantity" in user_crafty_data:
            limit_server_creation = user_crafty_data["server_quantity"].get(
                EnumPermissionsCrafty.SERVER_CREATION.name, 0
            )

            limit_user_creation = user_crafty_data["server_quantity"].get(
                EnumPermissionsCrafty.USER_CONFIG.name, 0
            )
            limit_role_creation = user_crafty_data["server_quantity"].get(
                EnumPermissionsCrafty.ROLES_CONFIG.name, 0
            )
        else:
            limit_server_creation = 0
            limit_user_creation = 0
            limit_role_creation = 0

        PermissionsCrafty.add_or_update_user(
            user_id,
            permissions_mask,
            limit_server_creation,
            limit_user_creation,
            limit_role_creation,
        )

        self.users_helper.delete_user_roles(user_id, removed_roles)

        self.users_helper.update_user(user_id, up_data)

    def raw_update_user(self, user_id: int, up_data: t.Optional[t.Dict[str, t.Any]]):
        """Directly passes the data to the model helper.

        Args:
            user_id (int): The id of the user to update.
            up_data (t.Optional[t.Dict[str, t.Any]]): Update data.
        """
        self.users_helper.update_user(user_id, up_data)

    def add_user(
        self,
        username,
        password,
        email="default@example.com",
        enabled: bool = True,
        superuser: bool = False,
    ):
        return self.users_helper.add_user(
            username,
            password=password,
            email=email,
            enabled=enabled,
            superuser=superuser,
        )

    @staticmethod
    def add_rawpass_user(
        username,
        password,
        email="default@example.com",
        enabled: bool = True,
        superuser: bool = False,
    ):
        return HelperUsers.add_rawpass_user(
            username,
            password=password,
            email=email,
            enabled=enabled,
            superuser=superuser,
        )

    def remove_user(self, user_id):
        return self.users_helper.remove_user(user_id)

    @staticmethod
    def user_id_exists(user_id):
        return HelperUsers.user_id_exists(user_id)

    @staticmethod
    def set_prepare(user_id):
        return HelperUsers.set_prepare(user_id)

    @staticmethod
    def stop_prepare(user_id):
        return HelperUsers.stop_prepare(user_id)

    def get_user_id_by_api_token(self, token: str) -> str:
        token_data = self.authentication.check_no_iat(token)
        return token_data["user_id"]

    def get_user_by_api_token(self, token: str):
        _, _, user = self.authentication.check_err(token)
        return user

    def get_api_key_by_token(self, token: str):
        key, _, _ = self.authentication.check(token)
        return key

    # **********************************************************************************
    #                                   User Roles Methods
    # **********************************************************************************

    @staticmethod
    def get_user_roles_id(user_id):
        return HelperUsers.get_user_roles_id(user_id)

    @staticmethod
    def get_user_roles_names(user_id):
        return HelperUsers.get_user_roles_names(user_id)

    def add_role_to_user(self, user_id, role_id):
        return self.users_helper.add_role_to_user(user_id, role_id)

    def add_user_roles(self, user):
        return self.users_helper.add_user_roles(user)

    @staticmethod
    def user_role_query(user_id):
        return HelperUsers.user_role_query(user_id)

    # **********************************************************************************
    #                                   Api Keys Methods
    # **********************************************************************************

    @staticmethod
    def get_user_api_keys(user_id: str):
        return HelperUsers.get_user_api_keys(user_id)

    @staticmethod
    def get_user_api_key(key_id: str):
        return HelperUsers.get_user_api_key(key_id)

    def add_user_api_key(
        self,
        name: str,
        user_id: str,
        superuser: bool = False,
        server_permissions_mask: t.Optional[str] = None,
        crafty_permissions_mask: t.Optional[str] = None,
    ):
        return self.users_helper.add_user_api_key(
            name, user_id, superuser, server_permissions_mask, crafty_permissions_mask
        )

    def delete_user_api_keys(self, user_id: str):
        return self.users_helper.delete_user_api_keys(user_id)

    def delete_user_api_key(self, key_id: str):
        return self.users_helper.delete_user_api_key(key_id)

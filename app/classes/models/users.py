import logging
import datetime
import typing as t

from peewee import (
    ForeignKeyField,
    CharField,
    AutoField,
    DateTimeField,
    BooleanField,
    CompositeKey,
    DoesNotExist,
    JOIN,
)
from playhouse.shortcuts import model_to_dict

from app.classes.shared.helpers import Helpers
from app.classes.models.base_model import BaseModel
from app.classes.models.roles import Roles, HelperRoles

logger = logging.getLogger(__name__)

# **********************************************************************************
#                                   Users Class
# **********************************************************************************
class Users(BaseModel):
    user_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_login = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    last_ip = CharField(default="")
    username = CharField(default="", unique=True, index=True)
    password = CharField(default="")
    email = CharField(default="default@example.com")
    enabled = BooleanField(default=True)
    superuser = BooleanField(default=False)
    lang = CharField(default="en_EN")
    support_logs = CharField(default="")
    valid_tokens_from = DateTimeField(default=datetime.datetime.now)
    server_order = CharField(default="")
    preparing = BooleanField(default=False)
    hints = BooleanField(default=True)

    class Meta:
        table_name = "users"


PUBLIC_USER_ATTRS: t.Final = [
    "user_id",
    "created",
    "username",
    "enabled",
    "superuser",
    "lang",  # maybe remove?
]

# **********************************************************************************
#                                   API Keys Class
# **********************************************************************************
class ApiKeys(BaseModel):
    token_id = AutoField()
    name = CharField(default="", unique=True, index=True)
    created = DateTimeField(default=datetime.datetime.now)
    user_id = ForeignKeyField(Users, backref="api_token", index=True)
    server_permissions = CharField(default="00000000")
    crafty_permissions = CharField(default="000")
    superuser = BooleanField(default=False)

    class Meta:
        table_name = "api_keys"


# **********************************************************************************
#                                   User Roles Class
# **********************************************************************************
class UserRoles(BaseModel):
    user_id = ForeignKeyField(Users, backref="user_role")
    role_id = ForeignKeyField(Roles, backref="user_role")

    class Meta:
        table_name = "user_roles"
        primary_key = CompositeKey("user_id", "role_id")


# **********************************************************************************
#                                   Users Helpers
# **********************************************************************************
class HelperUsers:
    def __init__(self, database, helper):
        self.database = database
        self.helper = helper

    @staticmethod
    def get_by_id(user_id):
        return Users.get_by_id(user_id)

    @staticmethod
    def get_all_users():
        query = Users.select().where(Users.username != "system")
        return query

    @staticmethod
    def get_all_usernames():
        usernames = []
        query = Users.select().where(Users.username != "system")
        for user in query:
            usernames.append(user.username)
        return usernames

    @staticmethod
    def get_all_user_ids() -> t.List[int]:
        return [
            user.user_id
            for user in Users.select(Users.user_id)
            .where(Users.username != "system")
            .execute()
        ]

    @staticmethod
    def get_user_lang_by_id(user_id):
        return Users.get(Users.user_id == user_id).lang

    @staticmethod
    def get_user_id_by_name(username):
        try:
            return (Users.get(Users.username == username)).user_id
        except DoesNotExist:
            return None

    @staticmethod
    def user_query(user_id):
        user_query = Users.select().where(Users.user_id == user_id)
        return user_query

    @staticmethod
    def get_user(user_id):
        if user_id == 0:
            return {
                "user_id": 0,
                "created": "10/24/2019, 11:34:00",
                "last_login": "10/24/2019, 11:34:00",
                "last_update": "10/24/2019, 11:34:00",
                "last_ip": "127.27.23.89",
                "username": "SYSTEM",
                "password": None,
                "email": "default@example.com",
                "enabled": True,
                "superuser": True,
                "roles": [],
                "servers": [],
                "support_logs": "",
            }
        user = model_to_dict(Users.get(Users.user_id == user_id))

        if user:
            # I know it should apply it without setting it but I'm just making sure
            user = HelperUsers.add_user_roles(user)
            return user
        # logger.debug("user: ({}) {}".format(user_id, {}))
        return {}

    @staticmethod
    def get_user_columns(
        user_id: t.Union[str, int], column_names: t.List[str]
    ) -> t.List[t.Any]:
        columns = [getattr(Users, column) for column in column_names]
        return model_to_dict(
            Users.select(*columns).where(Users.user_id == user_id).get(),
            only=columns,
        )

    @staticmethod
    def get_user_column(user_id: t.Union[str, int], column_name: str) -> t.Any:
        column = getattr(Users, column_name)
        return getattr(
            Users.select(column).where(Users.user_id == user_id).get(),
            column_name,
        )

    @staticmethod
    def get_user_model(user_id: str) -> Users:
        user = Users.get(Users.user_id == user_id)
        user = HelperUsers.add_user_roles(user)
        return user

    def add_user(
        self,
        username: str,
        password: str = None,
        email: t.Optional[str] = None,
        enabled: bool = True,
        superuser: bool = False,
    ) -> str:
        if password is not None:
            pw_enc = self.helper.encode_pass(password)
        else:
            pw_enc = None
        user_id = Users.insert(
            {
                Users.username: username.lower(),
                Users.password: pw_enc,
                Users.email: email,
                Users.enabled: enabled,
                Users.superuser: superuser,
                Users.created: Helpers.get_time_as_string(),
            }
        ).execute()
        return user_id

    @staticmethod
    def add_rawpass_user(
        username: str,
        password: str = "",
        email: t.Optional[str] = "default@example.com",
        enabled: bool = True,
        superuser: bool = False,
    ) -> str:
        user_id = Users.insert(
            {
                Users.username: username.lower(),
                Users.password: password,
                Users.email: email,
                Users.enabled: enabled,
                Users.superuser: superuser,
                Users.created: Helpers.get_time_as_string(),
            }
        ).execute()
        return user_id

    @staticmethod
    def update_user(user_id, up_data=None):
        if up_data is None:
            up_data = {}
        if up_data:
            Users.update(up_data).where(Users.user_id == user_id).execute()

    @staticmethod
    def update_server_order(user_id, user_server_order):
        Users.update(server_order=user_server_order).where(
            Users.user_id == user_id
        ).execute()

    @staticmethod
    def get_server_order(user_id):
        return Users.select().where(Users.user_id == user_id)

    @staticmethod
    def get_super_user_list():
        final_users: t.List[int] = []
        super_users = Users.select().where(
            Users.superuser == True  # pylint: disable=singleton-comparison
        )
        for suser in super_users:
            if suser.user_id not in final_users:
                final_users.append(suser.user_id)
        return final_users

    def remove_user(self, user_id):
        with self.database.atomic():
            UserRoles.delete().where(UserRoles.user_id == user_id).execute()
            return Users.delete().where(Users.user_id == user_id).execute()

    @staticmethod
    def set_support_path(user_id, support_path):
        Users.update(support_logs=support_path).where(
            Users.user_id == user_id
        ).execute()

    @staticmethod
    def set_prepare(user_id):
        Users.update(preparing=True).where(Users.user_id == user_id).execute()

    @staticmethod
    def stop_prepare(user_id):
        Users.update(preparing=False).where(Users.user_id == user_id).execute()

    @staticmethod
    def clear_support_status():
        Users.update(preparing=False).where(
            Users.preparing == True  # pylint: disable=singleton-comparison
        ).execute()

    @staticmethod
    def user_id_exists(user_id):
        return Users.select().where(Users.user_id == user_id).exists()

    # **********************************************************************************
    #                                   User_Roles Methods
    # **********************************************************************************

    @staticmethod
    def get_or_create(user_id, role_id):
        return UserRoles.get_or_create(user_id=user_id, role_id=role_id)

    @staticmethod
    def get_user_roles_id(user_id):
        roles_list = []
        roles = UserRoles.select().where(UserRoles.user_id == user_id)
        for r in roles:
            roles_list.append(HelperRoles.get_role(r.role_id)["role_id"])
        return roles_list

    @staticmethod
    def get_user_roles_names(user_id):
        roles = UserRoles.select(UserRoles.role_id).where(UserRoles.user_id == user_id)
        return [
            HelperRoles.get_role_column(role.role_id, "role_name") for role in roles
        ]

    @staticmethod
    def add_role_to_user(user_id, role_id):
        UserRoles.insert(
            {UserRoles.user_id: user_id, UserRoles.role_id: role_id}
        ).execute()

    @staticmethod
    def add_user_roles(user: t.Union[dict, Users]):
        if isinstance(user, dict):
            user_id = user["user_id"]
        else:
            user_id = user.user_id

        # I just copied this code from get_user,
        # it had those TODOs & comments made by mac - Lukas

        roles_query = (
            UserRoles.select()
            .join(Roles, JOIN.INNER)
            .where(UserRoles.user_id == user_id)
        )
        roles = {r.role_id_id for r in roles_query}

        if isinstance(user, dict):
            user["roles"] = roles
        else:
            user.roles = roles

        # logger.debug("user: ({}) {}".format(user_id, user))
        return user

    @staticmethod
    def user_role_query(user_id):
        user_query = UserRoles.select().where(UserRoles.user_id == user_id)
        query = Roles.select().where(Roles.role_id == -1)
        for user in user_query:
            query = query + Roles.select().where(Roles.role_id == user.role_id)
        return query

    @staticmethod
    def delete_user_roles(user_id, removed_roles):
        UserRoles.delete().where(UserRoles.user_id == user_id).where(
            UserRoles.role_id.in_(removed_roles)
        ).execute()

    @staticmethod
    def remove_roles_from_role_id(role_id):
        UserRoles.delete().where(UserRoles.role_id == role_id).execute()

    @staticmethod
    def get_users_from_role(role_id):
        UserRoles.select().where(UserRoles.role_id == role_id).execute()

    # **********************************************************************************
    #                                   ApiKeys Methods
    # **********************************************************************************

    @staticmethod
    def get_user_api_keys(user_id: str):
        return ApiKeys.select().where(ApiKeys.user_id == user_id).execute()

    @staticmethod
    def get_user_api_key(key_id: str) -> ApiKeys:
        return ApiKeys.get(ApiKeys.token_id == key_id)

    @staticmethod
    def add_user_api_key(
        name: str,
        user_id: str,
        superuser: bool = False,
        server_permissions_mask: t.Optional[str] = None,
        crafty_permissions_mask: t.Optional[str] = None,
    ):
        return ApiKeys.insert(
            {
                ApiKeys.name: name,
                ApiKeys.user_id: user_id,
                **(
                    {ApiKeys.server_permissions: server_permissions_mask}
                    if server_permissions_mask is not None
                    else {}
                ),
                **(
                    {ApiKeys.crafty_permissions: crafty_permissions_mask}
                    if crafty_permissions_mask is not None
                    else {}
                ),
                ApiKeys.superuser: superuser,
            }
        ).execute()

    @staticmethod
    def delete_user_api_keys(user_id: str):
        ApiKeys.delete().where(ApiKeys.user_id == user_id).execute()

    @staticmethod
    def delete_user_api_key(key_id: str):
        ApiKeys.delete().where(ApiKeys.token_id == key_id).execute()

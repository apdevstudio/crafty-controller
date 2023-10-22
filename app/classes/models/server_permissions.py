import logging
import typing as t
from enum import Enum
from peewee import (
    ForeignKeyField,
    CharField,
    CompositeKey,
    JOIN,
)

from app.classes.models.base_model import BaseModel
from app.classes.models.servers import Servers
from app.classes.models.roles import Roles
from app.classes.models.users import UserRoles, HelperUsers, ApiKeys, Users
from app.classes.shared.permission_helper import PermissionHelper

logger = logging.getLogger(__name__)


# **********************************************************************************
#                                  Role Servers Class
# **********************************************************************************
class RoleServers(BaseModel):
    role_id = ForeignKeyField(Roles, backref="role_server")
    server_uuid = ForeignKeyField(Servers, backref="role_server")
    permissions = CharField(default="00000000")

    class Meta:
        table_name = "role_servers"
        primary_key = CompositeKey("role_id", "server_uuid")


# **********************************************************************************
#                                  Servers Permissions Class
# **********************************************************************************
class EnumPermissionsServer(Enum):
    COMMANDS = 0
    TERMINAL = 1
    LOGS = 2
    SCHEDULE = 3
    BACKUP = 4
    FILES = 5
    CONFIG = 6
    PLAYERS = 7


class PermissionsServers:
    @staticmethod
    def get_or_create(role_id, server, permissions_mask):
        return RoleServers.get_or_create(
            role_id=role_id, server_uuid=server, permissions=permissions_mask
        )

    @staticmethod
    def get_permissions_list():
        return list(EnumPermissionsServer.__members__.values())

    @staticmethod
    def get_permissions(permissions_mask):
        return [
            permission
            for permission in EnumPermissionsServer.__members__.values()
            if PermissionsServers.has_permission(permissions_mask, permission)
        ]

    @staticmethod
    def has_permission(permission_mask, permission_tested: EnumPermissionsServer):
        return permission_mask[permission_tested.value] == "1"

    @staticmethod
    def set_permission(
        permission_mask, permission_tested: EnumPermissionsServer, value
    ):
        list_perms = list(permission_mask)
        list_perms[permission_tested.value] = str(value)
        permission_mask = "".join(list_perms)
        return permission_mask

    @staticmethod
    def get_permission(permission_mask, permission_tested: EnumPermissionsServer):
        return permission_mask[permission_tested.value]

    @staticmethod
    def get_token_permissions(permissions_mask, api_permissions_mask):
        return [
            permission
            for permission in EnumPermissionsServer.__members__.values()
            if PermissionHelper.both_have_perm(
                permissions_mask, api_permissions_mask, permission
            )
        ]

    # **********************************************************************************
    #                                   Role_Servers Methods
    # **********************************************************************************
    @staticmethod
    def get_role_servers_from_role_id(roleid: t.Union[str, int]):
        return RoleServers.select().where(RoleServers.role_id == roleid)

    @staticmethod
    def get_servers_from_role(role_id: t.Union[str, int]):
        return (
            RoleServers.select()
            .join(Servers, JOIN.INNER)
            .where(RoleServers.role_id == role_id)
        )

    @staticmethod
    def get_server_uuids_from_role(role_id: t.Union[str, int]) -> t.List[int]:
        # FIXME: somehow retrieve only the server ids, not the whole servers
        return [
            role_servers.server_uuid.server_uuid
            for role_servers in (
                RoleServers.select(RoleServers.server_uuid).where(
                    RoleServers.role_id == role_id
                )
            )
        ]

    @staticmethod
    def get_roles_from_server(server_uuid):
        return (
            RoleServers.select()
            .join(Roles, JOIN.INNER)
            .where(RoleServers.server_uuid == server_uuid)
        )

    @staticmethod
    def add_role_server(server_uuid, role_id, rs_permissions="00000000"):
        servers = RoleServers.insert(
            {
                RoleServers.server_uuid: server_uuid,
                RoleServers.role_id: role_id,
                RoleServers.permissions: rs_permissions,
            }
        ).execute()
        return servers

    @staticmethod
    def get_permissions_mask(role_id, server_uuid):
        permissions_mask = ""
        role_server = (
            RoleServers.select()
            .where(RoleServers.role_id == role_id)
            .where(RoleServers.server_uuid == server_uuid)
            .get()
        )
        permissions_mask = role_server.permissions
        return permissions_mask

    @staticmethod
    def get_server_roles(server_uuid):
        role_list = []
        roles = (
            RoleServers.select().where(RoleServers.server_uuid == server_uuid).execute()
        )
        for role in roles:
            role_list.append(role.role_id)
        return role_list

    @staticmethod
    def get_role_permissions_list(role_id):
        role_server = RoleServers.get_or_none(RoleServers.role_id == role_id)
        permissions_mask = (
            "00000000" if role_server is None else role_server.permissions
        )
        permissions_list = PermissionsServers.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def get_role_permissions_dict(role_id):
        permissions_dict: t.Dict[str, t.List[EnumPermissionsServer]] = {}
        role_servers = RoleServers.select(
            RoleServers.server_uuid, RoleServers.permissions
        ).where(RoleServers.role_id == role_id)
        for role_server in role_servers:
            permissions_dict[
                role_server.server_uuid
            ] = PermissionsServers.get_permissions(role_server.permissions)
        return permissions_dict

    @staticmethod
    def update_role_permission(role_id, server_uuid, permissions_mask):
        RoleServers.update(permissions=permissions_mask).where(
            RoleServers.role_id == role_id, RoleServers.server_uuid == server_uuid
        ).execute()

    @staticmethod
    def delete_roles_permissions(
        role_id: t.Union[str, int], removed_servers: t.Sequence[t.Union[str, int]]
    ):
        return (
            RoleServers.delete()
            .where(RoleServers.role_id == role_id)
            .where(RoleServers.server_uuid.in_(removed_servers))
            .execute()
        )

    @staticmethod
    def remove_roles_of_server(server_uuid):
        return (
            RoleServers.delete().where(RoleServers.server_uuid == server_uuid).execute()
        )

    @staticmethod
    def get_user_id_permissions_mask(user_id, server_uuid: str):
        user = HelperUsers.get_user_model(user_id)
        return PermissionsServers.get_user_permissions_mask(user, server_uuid)

    @staticmethod
    def get_user_permissions_mask(user: Users, server_uuid: str):
        if user.superuser:
            permissions_mask = "1" * len(EnumPermissionsServer)
        else:
            roles_list = HelperUsers.get_user_roles_id(user.user_id)
            role_server = (
                RoleServers.select()
                .where(RoleServers.role_id.in_(roles_list))
                .where(RoleServers.server_uuid == server_uuid)
                .execute()
            )
            try:
                permissions_mask = role_server[0].permissions
            except IndexError:
                permissions_mask = "0" * len(EnumPermissionsServer)
        return permissions_mask

    @staticmethod
    def get_server_user_list(server_uuid):
        final_users = []
        server_roles = RoleServers.select().where(
            RoleServers.server_uuid == server_uuid
        )
        super_users = Users.select(Users.user_id).where(
            Users.superuser == True  # pylint: disable=singleton-comparison
        )
        for role in server_roles:
            users = UserRoles.select(UserRoles.user_id).where(
                UserRoles.role_id == role.role_id
            )
            for user in users:
                if user.user_id_id not in final_users:
                    final_users.append(user.user_id_id)
        for suser in super_users:
            if suser.user_id not in final_users:
                final_users.append(suser.user_id)
        return final_users

    @staticmethod
    def get_user_id_permissions_list(user_id, server_uuid: str):
        user = HelperUsers.get_user_model(user_id)
        return PermissionsServers.get_user_permissions_list(user, server_uuid)

    @staticmethod
    def get_user_permissions_list(user: Users, server_uuid: str):
        if user.superuser:
            permissions_list = PermissionsServers.get_permissions_list()
        else:
            permissions_mask = PermissionsServers.get_user_permissions_mask(
                user, server_uuid
            )
            permissions_list = PermissionsServers.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def get_api_key_id_permissions_list(key_id, server_uuid: str):
        key = ApiKeys.get(ApiKeys.token_id == key_id)
        return PermissionsServers.get_api_key_permissions_list(key, server_uuid)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys, server_uuid: str):
        user = HelperUsers.get_user(key.user_id)
        if user["superuser"] and key.superuser:
            return PermissionsServers.get_permissions_list()
        roles_list = HelperUsers.get_user_roles_id(user["user_id"])
        role_server = (
            RoleServers.select()
            .where(RoleServers.role_id.in_(roles_list))
            .where(RoleServers.server_uuid == server_uuid)
            .execute()
        )
        try:
            user_permissions_mask = role_server[0].permissions
        except:
            if user["superuser"]:
                user_permissions_mask = "11111111"
            else:
                user_permissions_mask = "00000000"
        key_permissions_mask = key.server_permissions
        permissions_mask = PermissionHelper.combine_masks(
            user_permissions_mask, key_permissions_mask
        )
        permissions_list = PermissionsServers.get_permissions(permissions_mask)
        return permissions_list

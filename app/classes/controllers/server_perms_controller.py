import logging
from app.classes.controllers.servers_controller import ServersController

from app.classes.models.server_permissions import (
    PermissionsServers,
    EnumPermissionsServer,
)
from app.classes.models.users import HelperUsers, ApiKeys
from app.classes.models.roles import HelperRoles
from app.classes.models.servers import HelperServers

logger = logging.getLogger(__name__)


class ServerPermsController:
    @staticmethod
    def get_server_user_list(server_uuid):
        return PermissionsServers.get_server_user_list(server_uuid)

    @staticmethod
    def list_defined_permissions():
        permissions_list = PermissionsServers.get_permissions_list()
        return permissions_list

    @staticmethod
    def get_mask_permissions(role_id, server_uuid):
        permissions_mask = PermissionsServers.get_permissions_mask(role_id, server_uuid)
        return permissions_mask

    @staticmethod
    def get_role_permissions_dict(role_id):
        return PermissionsServers.get_role_permissions_dict(role_id)

    @staticmethod
    def add_role_server(server_uuid, role_id, rs_permissions="00000000"):
        return PermissionsServers.add_role_server(server_uuid, role_id, rs_permissions)

    @staticmethod
    def get_server_roles(server_uuid):
        return PermissionsServers.get_server_roles(server_uuid)

    @staticmethod
    def backup_role_swap(old_server_uuid, new_server_uuid):
        role_list = PermissionsServers.get_server_roles(old_server_uuid)
        for role in role_list:
            PermissionsServers.add_role_server(
                new_server_uuid,
                role.role_id,
                PermissionsServers.get_permissions_mask(
                    int(role.role_id), int(old_server_uuid)
                ),
            )
            # Permissions_Servers.add_role_server(
            #     new_server_uuid, role.role_id, "00001000"
            # )

    # **********************************************************************************
    #                                   Servers Permissions Methods
    # **********************************************************************************
    @staticmethod
    def get_permissions_mask(role_id, server_uuid):
        return PermissionsServers.get_permissions_mask(role_id, server_uuid)

    @staticmethod
    def set_permission(
        permission_mask, permission_tested: EnumPermissionsServer, value
    ):
        return PermissionsServers.set_permission(
            permission_mask, permission_tested, value
        )

    @staticmethod
    def get_user_id_permissions_list(user_id: str, server_uuid: str):
        return PermissionsServers.get_user_id_permissions_list(user_id, server_uuid)

    @staticmethod
    def get_api_key_id_permissions_list(key_id: str, server_uuid: str):
        key = HelperUsers.get_user_api_key(key_id)
        return PermissionsServers.get_api_key_permissions_list(key, server_uuid)

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys, server_uuid: str):
        return PermissionsServers.get_api_key_permissions_list(key, server_uuid)

    @staticmethod
    def get_authorized_servers_stats_from_roles(user_id):
        user_roles = HelperUsers.get_user_roles_id(user_id)
        roles_list = []
        role_server = []
        authorized_servers = []
        server_data = []

        for user in user_roles:
            roles_list.append(HelperRoles.get_role(user.role_id))

        for role in roles_list:
            role_test = PermissionsServers.get_role_servers_from_role_id(
                role.get("role_id")
            )
            for test in role_test:
                role_server.append(test)

        for server in role_server:
            authorized_servers.append(
                HelperServers.get_server_data_by_id(server.server_uuid)
            )

        for server in authorized_servers:
            srv = ServersController().get_server_instance_by_id(
                server.get("server_uuid")
            )
            latest = srv.stats_helper.get_latest_server_stats()
            server_data.append(
                {
                    "server_data": server,
                    "stats": latest,
                }
            )
        return server_data

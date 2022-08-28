import logging
import typing as t

from app.classes.models.roles import HelperRoles
from app.classes.models.server_permissions import PermissionsServers, RoleServers
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)


class RolesController:
    def __init__(self, users_helper, roles_helper):
        self.users_helper = users_helper
        self.roles_helper = roles_helper

    @staticmethod
    def get_all_roles():
        return HelperRoles.get_all_roles()

    @staticmethod
    def get_all_role_ids():
        return HelperRoles.get_all_role_ids()

    @staticmethod
    def get_roleid_by_name(role_name):
        return HelperRoles.get_roleid_by_name(role_name)

    @staticmethod
    def get_role(role_id):
        return HelperRoles.get_role(role_id)

    @staticmethod
    def update_role(role_id: str, role_data=None, permissions_mask: str = "00000000"):
        if role_data is None:
            role_data = {}
        base_data = RolesController.get_role_with_servers(role_id)
        up_data = {}
        added_servers = set()
        removed_servers = set()
        for key in role_data:
            if key == "role_id":
                continue
            if key == "servers":
                added_servers = set(role_data["servers"]).difference(
                    set(base_data["servers"])
                )
                removed_servers = set(base_data["servers"]).difference(
                    set(role_data["servers"])
                )
            elif base_data[key] != role_data[key]:
                up_data[key] = role_data[key]
        up_data["last_update"] = Helpers.get_time_as_string()
        logger.debug(
            f"role: {role_data} +server:{added_servers} -server{removed_servers}"
        )
        for server in added_servers:
            PermissionsServers.get_or_create(role_id, server, permissions_mask)
        for server in base_data["servers"]:
            PermissionsServers.update_role_permission(role_id, server, permissions_mask)
            # TODO: This is horribly inefficient and we should be using bulk queries
            # but im going for functionality at this point
        PermissionsServers.delete_roles_permissions(role_id, removed_servers)
        if up_data:
            HelperRoles.update_role(role_id, up_data)

    @staticmethod
    def add_role(role_name, manager):
        return HelperRoles.add_role(role_name, manager)

    class RoleServerJsonType(t.TypedDict):
        server_id: t.Union[str, int]
        permissions: str

    @staticmethod
    def get_server_ids_and_perms_from_role(
        role_id: t.Union[str, int]
    ) -> t.List[RoleServerJsonType]:
        # FIXME: somehow retrieve only the server ids, not the whole servers
        return [
            {
                "server_id": role_servers.server_id.server_id,
                "permissions": role_servers.permissions,
            }
            for role_servers in (
                RoleServers.select(
                    RoleServers.server_id, RoleServers.permissions
                ).where(RoleServers.role_id == role_id)
            )
        ]

    @staticmethod
    def add_role_advanced(
        name: str,
        servers: t.Iterable[RoleServerJsonType],
        manager: int,
    ) -> int:
        """Add a role with a name and a list of servers

        Args:
            name (str): The new role's name
            servers (t.List[RoleServerJsonType]): The new role's servers

        Returns:
            int: The new role's ID
        """
        role_id: t.Final[int] = HelperRoles.add_role(name, manager)
        for server in servers:
            PermissionsServers.get_or_create(
                role_id, server["server_id"], server["permissions"]
            )
        return role_id

    @staticmethod
    def update_role_advanced(
        role_id: t.Union[str, int],
        role_name: t.Optional[str],
        servers: t.Optional[t.Iterable[RoleServerJsonType]],
        manager: int,
    ) -> None:
        """Update a role with a name and a list of servers

        Args:
            role_id (t.Union[str, int]): The ID of the role to be modified
            role_name (t.Optional[str]): An optional new name for the role
            servers (t.Optional[t.Iterable[RoleServerJsonType]]): An optional list of servers for the role
        """  # pylint: disable=line-too-long
        logger.debug(f"updating role {role_id} with advanced options")

        if servers is not None:
            base_data = RolesController.get_role_with_servers(role_id)

            server_ids = {server["server_id"] for server in servers}
            server_permissions_map = {
                server["server_id"]: server["permissions"] for server in servers
            }

            added_servers = server_ids.difference(set(base_data["servers"]))
            removed_servers = set(base_data["servers"]).difference(server_ids)
            same_servers = server_ids.intersection(set(base_data["servers"]))
            logger.debug(
                f"role: {role_id} +server:{added_servers} -server{removed_servers}"
            )
            for server_id in added_servers:
                PermissionsServers.get_or_create(
                    role_id, server_id, server_permissions_map[server_id]
                )
            if len(removed_servers) != 0:
                PermissionsServers.delete_roles_permissions(role_id, removed_servers)
            for server_id in same_servers:
                PermissionsServers.update_role_permission(
                    role_id, server_id, server_permissions_map[server_id]
                )
        if role_name is not None:
            up_data = {
                "role_name": role_name,
                "last_update": Helpers.get_time_as_string(),
                "manager": manager,
            }
            # TODO: do the last_update on the db side
            HelperRoles.update_role(role_id, up_data)

    def remove_role(self, role_id):
        role_data = RolesController.get_role_with_servers(role_id)
        PermissionsServers.delete_roles_permissions(role_id, role_data["servers"])
        self.users_helper.remove_roles_from_role_id(role_id)
        return self.roles_helper.remove_role(role_id)

    @staticmethod
    def role_id_exists(role_id):
        return HelperRoles.role_id_exists(role_id)

    @staticmethod
    def get_role_with_servers(role_id):
        role = HelperRoles.get_role(role_id)

        if role:
            server_ids = PermissionsServers.get_server_ids_from_role(role_id)
            role["servers"] = server_ids
            # logger.debug("role: ({}) {}".format(role_id, role))
            return role
        # logger.debug("role: ({}) {}".format(role_id, {}))
        return {}

import os
import logging
import time
import json
import pathlib
import typing as t

from app.classes.controllers.roles_controller import RolesController
from app.classes.shared.file_helpers import FileHelpers

from app.classes.shared.singleton import Singleton
from app.classes.shared.server import ServerInstance
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_models import DatabaseShortcuts

from app.classes.minecraft.stats import Stats

from app.classes.models.servers import HelperServers
from app.classes.models.users import HelperUsers, ApiKeys
from app.classes.models.server_permissions import (
    PermissionsServers,
    EnumPermissionsServer,
)

logger = logging.getLogger(__name__)


class ServersController(metaclass=Singleton):
    servers_list: ServerInstance

    def __init__(self, helper, servers_helper, management_helper, file_helper):
        self.helper: Helpers = helper
        self.file_helper: FileHelpers = file_helper
        self.servers_helper: HelperServers = servers_helper
        self.management_helper = management_helper
        self.servers_list = []
        self.stats = Stats(self.helper, self)

    # **********************************************************************************
    #                                   Generic Servers Methods
    # **********************************************************************************
    def create_server(
        self,
        name: str,
        server_uuid: str,
        server_dir: str,
        backup_path: str,
        server_command: str,
        server_file: str,
        server_log_file: str,
        server_stop: str,
        server_type: str,
        server_port: int = 25565,
        server_host: str = "127.0.0.1",
    ) -> int:
        """Create a server in the database

        Args:
            name: The name of the server
            server_uuid: This is the UUID of the server
            server_dir: The directory where the server is located
            backup_path: The path to the backup folder
            server_command: The command to start the server
            server_file: The name of the server file
            server_log_file: The path to the server log file
            server_stop: This is the command to stop the server
            server_type: This is the type of server you're creating.
            server_port: The port the server will be monitored on, defaults to 25565
            server_host: The host the server will be monitored on, defaults to 127.0.0.1

        Returns:
            int: The new server's id

        Raises:
            PeeweeException: If the server already exists
        """
        return HelperServers.create_server(
            name,
            server_uuid,
            server_dir,
            backup_path,
            server_command,
            server_file,
            server_log_file,
            server_stop,
            server_type,
            server_port,
            server_host,
        )

    @staticmethod
    def get_server_obj(server_id):
        return HelperServers.get_server_obj(server_id)

    @staticmethod
    def update_server(server_obj):
        ret = HelperServers.update_server(server_obj)
        server_instance: ServerInstance = ServersController().get_server_instance_by_id(
            server_obj.server_id
        )
        server_instance.update_server_instance()
        return ret

    @staticmethod
    def set_download(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.set_download()

    @staticmethod
    def finish_download(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.finish_download()

    @staticmethod
    def get_download_status(server_id):
        server = ServersController().get_server_instance_by_id(server_id)
        return server.stats_helper.get_download_status()

    def remove_server(self, server_id):
        roles_list = PermissionsServers.get_roles_from_server(server_id)
        for role in roles_list:
            role_id = role.role_id
            role_data = RolesController.get_role_with_servers(role_id)
            role_data["servers"] = {server_id}
            PermissionsServers.delete_roles_permissions(role_id, role_data["servers"])
        PermissionsServers.remove_roles_of_server(server_id)
        self.servers_helper.remove_server(server_id)

    @staticmethod
    def get_server_data_by_id(server_id):
        return HelperServers.get_server_data_by_id(server_id)

    # **********************************************************************************
    #                                     Servers Methods
    # **********************************************************************************

    def get_server_instance_by_id(self, server_id: t.Union[str, int]) -> ServerInstance:
        for server in self.servers_list:
            if int(server["server_id"]) == int(server_id):
                return server["server_obj"]

        logger.warning(f"Unable to find server object for server id {server_id}")
        raise Exception(f"Unable to find server object for server id {server_id}")

    def init_all_servers(self):

        servers = self.get_all_defined_servers()

        for server in servers:
            server_id = server.get("server_id")

            # if we have already initialized this server, let's skip it.
            if self.check_server_loaded(server_id):
                continue

            # if this server path no longer exists - let's warn and bomb out
            if not Helpers.check_path_exists(
                Helpers.get_os_understandable_path(server["path"])
            ):
                logger.warning(
                    f"Unable to find server "
                    f"{server['server_name']} at path {server['path']}. "
                    f"Skipping this server"
                )

                Console.warning(
                    f"Unable to find server "
                    f"{server['server_name']} at path {server['path']}. "
                    f"Skipping this server"
                )
                continue

            temp_server_dict = {
                "server_id": server.get("server_id"),
                "server_data_obj": server,
                "server_obj": ServerInstance(
                    server.get("server_id"),
                    self.helper,
                    self.management_helper,
                    self.stats,
                    self.file_helper,
                ),
            }

            # setup the server, do the auto start and all that jazz
            temp_server_dict["server_obj"].do_server_setup(server)

            # add this temp object to the list of init servers
            self.servers_list.append(temp_server_dict)

            if server["auto_start"]:
                self.set_waiting_start(server["server_id"], True)

            self.refresh_server_settings(server["server_id"])

            Console.info(
                f"Loaded Server: ID {server['server_id']}"
                f" | Name: {server['server_name']}"
                f" | Autostart: {server['auto_start']}"
                f" | Delay: {server['auto_start_delay']}"
            )

    def check_server_loaded(self, server_id_to_check: int):

        logger.info(f"Checking to see if we already registered {server_id_to_check}")

        for server in self.servers_list:
            known_server = server.get("server_id")
            if known_server is None:
                return False

            if known_server == server_id_to_check:
                logger.info(
                    f"skipping initialization of server {server_id_to_check} "
                    f"because it is already loaded"
                )
                return True

        return False

    def refresh_server_settings(self, server_id: int):
        server_obj = self.get_server_instance_by_id(server_id)
        server_obj.reload_server_settings()

    @staticmethod
    def get_all_defined_servers():
        return HelperServers.get_all_defined_servers()

    @staticmethod
    def get_authorized_servers(user_id):
        server_data: t.List[t.Dict[str, t.Any]] = []
        user_roles = HelperUsers.user_role_query(user_id)
        for user in user_roles:
            role_servers = PermissionsServers.get_role_servers_from_role_id(
                user.role_id
            )
            for role in role_servers:
                server_data.append(
                    ServersController().get_server_instance_by_id(
                        role.server_id.server_id
                    )
                )

        return server_data

    @staticmethod
    def get_authorized_users(server_id: str):
        user_ids: t.Set[int] = set()
        roles_list = PermissionsServers.get_roles_from_server(server_id)
        for role in roles_list:
            role_users = HelperUsers.get_users_from_role(role.role_id)
            for user_role in role_users:
                user_ids.add(user_role.user_id)

        for user_id in HelperUsers.get_super_user_list():
            user_ids.add(user_id)

        return user_ids

    def get_all_servers_stats(self):
        server_data = []
        try:
            for server in self.servers_list:
                srv: ServerInstance = ServersController().get_server_instance_by_id(
                    server.get("server_id")
                )
                latest = srv.stats_helper.get_latest_server_stats()
                server_data.append(
                    {
                        "server_data": DatabaseShortcuts.get_data_obj(
                            srv.server_object
                        ),
                        "stats": latest,
                        "user_command_permission": True,
                    }
                )
        except IndexError as ex:
            logger.error(
                f"Stats collection failed with error: {ex}. Was a server just created?"
            )
        return server_data

    @staticmethod
    def get_authorized_servers_stats_api_key(api_key: ApiKeys):
        server_data = []
        authorized_servers = ServersController().get_authorized_servers(
            api_key.user_id  # TODO: API key authorized servers?
        )

        for server in authorized_servers:
            srv: ServerInstance = server
            latest = srv.stats_helper.get_latest_server_stats()
            key_permissions = PermissionsServers.get_api_key_permissions_list(
                api_key, server.server_id
            )
            if EnumPermissionsServer.COMMANDS in key_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append(
                {
                    "server_data": DatabaseShortcuts.get_data_obj(server.server_object),
                    "stats": latest,
                    "user_command_permission": user_command_permission,
                }
            )
        return server_data

    @staticmethod
    def get_authorized_servers_stats(user_id):
        server_data = []
        authorized_servers = ServersController.get_authorized_servers(user_id)

        for server in authorized_servers:
            srv: ServerInstance = server
            latest = srv.stats_helper.get_latest_server_stats()
            # TODO
            user_permissions = PermissionsServers.get_user_id_permissions_list(
                user_id, server.server_id
            )
            if EnumPermissionsServer.COMMANDS in user_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append(
                {
                    "server_data": DatabaseShortcuts.get_data_obj(srv.server_object),
                    "stats": latest,
                    "user_command_permission": user_command_permission,
                }
            )

        return server_data

    @staticmethod
    def get_server_friendly_name(server_id):
        return HelperServers.get_server_friendly_name(server_id)

    def crash_detection(self, server_obj):
        svr = self.get_server_instance_by_id(server_obj.server_id)
        # start or stop crash detection depending upon user preference
        # The below functions check to see if the server is running.
        # They only execute if it's running.
        if server_obj.crash_detection == 1:
            svr.start_crash_detection()
        else:
            svr.stop_crash_detection()

    def get_server_obj_optional(
        self, server_id: t.Union[str, int]
    ) -> t.Optional[ServerInstance]:
        for server in self.servers_list:
            if str(server["server_id"]) == str(server_id):
                return server["server_obj"]

        logger.warning(f"Unable to find server object for server id {server_id}")
        return None

    def get_server_data(self, server_id: str):
        for server in self.servers_list:
            if str(server["server_id"]) == str(server_id):
                return server["server_data_obj"]

        logger.warning(f"Unable to find server object for server id {server_id}")
        return False

    def list_defined_servers(self):
        defined_servers = []
        for server in self.servers_list:
            defined_servers.append(
                self.get_server_instance_by_id(server.get("server_id"))
            )
        return defined_servers

    @staticmethod
    def get_all_server_ids() -> t.List[int]:
        return HelperServers.get_all_server_ids()

    def list_running_servers(self):
        running_servers = []

        # for each server
        for server in self.servers_list:
            # is the server running?
            srv_obj: ServerInstance = server["server_obj"]
            running = srv_obj.check_running()
            # if so, let's add a dictionary to the list of running servers
            if running:
                running_servers.append({"id": srv_obj.server_id, "name": srv_obj.name})

        return running_servers

    def stop_all_servers(self):
        servers = self.list_running_servers()
        logger.info(f"Found {len(servers)} running server(s)")
        Console.info(f"Found {len(servers)} running server(s)")

        logger.info("Stopping All Servers")
        Console.info("Stopping All Servers")

        for server in servers:
            logger.info(f"Stopping Server ID {server['id']} - {server['name']}")
            Console.info(f"Stopping Server ID {server['id']} - {server['name']}")

            self.stop_server(server["id"])

            # let's wait 2 seconds to let everything flush out
            time.sleep(2)

        logger.info("All Servers Stopped")
        Console.info("All Servers Stopped")

    def stop_server(self, server_id):
        # issue the stop command
        svr_obj = self.get_server_instance_by_id(server_id)
        svr_obj.stop_threaded_server()

    # **********************************************************************************
    #                                    Servers_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_server_stats_by_id(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.get_latest_server_stats()

    @staticmethod
    def server_id_exists(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.server_id_exists()

    @staticmethod
    def get_server_type_by_id(server_id):
        return HelperServers.get_server_type_by_id(server_id)

    @staticmethod
    def server_id_authorized(server_id_a, user_id):
        user_roles = HelperUsers.user_role_query(user_id)
        for role in user_roles:
            for server_id_b in PermissionsServers.get_role_servers_from_role_id(
                role.role_id
            ):
                if str(server_id_a) == str(server_id_b.server_id):
                    return True
        return False

    @staticmethod
    def is_crashed(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.is_crashed()

    @staticmethod
    def server_id_authorized_api_key(server_id: str, api_key: ApiKeys) -> bool:
        # TODO
        return ServersController.server_id_authorized(server_id, api_key.user.user_id)
        # There is no view server permission
        # permission_helper.both_have_perm(api_key)

    @staticmethod
    def set_update(server_id, value):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.set_update(value)

    @staticmethod
    def get_ttl_without_player(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.get_ttl_without_player()

    @staticmethod
    def can_stop_no_players(server_id, time_limit):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.can_stop_no_players(time_limit)

    @staticmethod
    def set_waiting_start(server_id, value):
        srv = ServersController().get_server_instance_by_id(server_id)
        srv.stats_helper.set_waiting_start(value)

    @staticmethod
    def get_waiting_start(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.get_waiting_start()

    @staticmethod
    def get_update_status(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        return srv.stats_helper.get_update_status()

    # **********************************************************************************
    #                                    Servers Helpers Methods
    # **********************************************************************************
    @staticmethod
    def get_banned_players(server_id):
        srv = ServersController().get_server_instance_by_id(server_id)
        stats = srv.stats_helper.get_server_stats()
        server_path = stats["server_id"]["path"]
        path = os.path.join(server_path, "banned-players.json")

        try:
            with open(
                Helpers.get_os_understandable_path(path), encoding="utf-8"
            ) as file:
                content = file.read()
                file.close()
        except Exception as ex:
            print(ex)
            return None

        return json.loads(content)

    def check_for_old_logs(self):
        servers = HelperServers.get_all_defined_servers()
        for server in servers:
            logs_path, latest_log_file = os.path.split(server["log_path"])
            logs_delete_after = int(server["logs_delete_after"])
            if logs_delete_after == 0:
                continue

            log_files = list(
                filter(
                    lambda val: val != latest_log_file,
                    os.listdir(
                        pathlib.Path(
                            server["path"], os.path.split(server["log_path"])[0]
                        )
                    ),
                )
            )
            for log_file in log_files:
                log_file_path = os.path.join(logs_path, log_file)
                if Helpers.check_file_exists(
                    log_file_path
                ) and Helpers.is_file_older_than_x_days(
                    log_file_path, logs_delete_after
                ):
                    os.remove(log_file_path)

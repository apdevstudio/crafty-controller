import os
import pathlib
from pathlib import Path
from datetime import datetime
import platform
import shutil
import time
import json
import logging
import threading
from peewee import DoesNotExist

# TZLocal is set as a hidden import on win pipeline
from tzlocal import get_localzone
from tzlocal.utils import ZoneInfoNotFoundError
from apscheduler.schedulers.background import BackgroundScheduler

from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.models.users import HelperUsers
from app.classes.models.roles import HelperRoles
from app.classes.models.management import HelpersManagement
from app.classes.models.servers import HelperServers
from app.classes.controllers.crafty_perms_controller import CraftyPermsController
from app.classes.controllers.management_controller import ManagementController
from app.classes.controllers.users_controller import UsersController
from app.classes.controllers.roles_controller import RolesController
from app.classes.controllers.server_perms_controller import ServerPermsController
from app.classes.controllers.servers_controller import ServersController
from app.classes.shared.authentication import Authentication
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.shared.file_helpers import FileHelpers
from app.classes.shared.import_helper import ImportHelpers
from app.classes.minecraft.serverjars import ServerJars

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, database, helper, file_helper, import_helper):
        self.helper: Helpers = helper
        self.file_helper: FileHelpers = file_helper
        self.import_helper: ImportHelpers = import_helper
        self.server_jars: ServerJars = ServerJars(helper)
        self.users_helper: HelperUsers = HelperUsers(database, self.helper)
        self.roles_helper: HelperRoles = HelperRoles(database)
        self.servers_helper: HelperServers = HelperServers(database)
        self.management_helper: HelpersManagement = HelpersManagement(
            database, self.helper
        )
        self.authentication: Authentication = Authentication(self.helper)
        self.crafty_perms: CraftyPermsController = CraftyPermsController()
        self.management: ManagementController = ManagementController(
            self.management_helper
        )
        self.roles: RolesController = RolesController(
            self.users_helper, self.roles_helper
        )
        self.server_perms: ServerPermsController = ServerPermsController()
        self.servers: ServersController = ServersController(
            self.helper, self.servers_helper, self.management_helper, self.file_helper
        )
        self.users: UsersController = UsersController(
            self.helper, self.users_helper, self.authentication
        )
        try:
            tz = get_localzone()
        except ZoneInfoNotFoundError:
            logger.error(
                "Could not capture time zone from system. Falling back to Europe/London"
            )
            tz = "Europe/London"
        self.support_scheduler: BackgroundScheduler = BackgroundScheduler(
            timezone=str(tz)
        )
        self.first_login = False
        self.cached_login = self.management.get_login_image()
        self.support_scheduler.start()

    @staticmethod
    def check_system_user():
        return HelperUsers.get_user_id_by_name("system") is not None

    def set_project_root(self, root_dir):
        self.project_root = root_dir

    def set_config_json(self, data):
        current_config = self.helper.get_all_settings()
        for key in current_config:
            if key in data:
                current_config[key] = data[key]
        keys = list(current_config.keys())
        keys.sort()
        sorted_data = {i: current_config[i] for i in keys}
        with open(self.helper.settings_file, "w", encoding="utf-8") as f:
            json.dump(sorted_data, f, indent=4)

    def package_support_logs(self, exec_user):
        if exec_user["preparing"]:
            return
        self.users.set_prepare(exec_user["user_id"])
        logger.info("Checking for previous support logs.")
        if exec_user["support_logs"] != "":
            if os.path.exists(exec_user["support_logs"]):
                logger.info(
                    f"Found previous support log request at {exec_user['support_logs']}"
                )
                if self.helper.validate_traversal(
                    os.path.join(self.project_root, "temp"), exec_user["support_logs"]
                ):
                    logger.debug("No transversal detected. Going for the delete.")
                    self.del_support_file(exec_user["support_logs"])
        # pausing so on screen notifications can run for user
        time.sleep(7)
        self.helper.websocket_helper.broadcast_user(
            exec_user["user_id"], "notification", "Preparing your support logs"
        )
        self.helper.ensure_dir_exists(
            os.path.join(self.project_root, "temp", str(exec_user["user_id"]))
        )
        temp_dir = os.path.join(
            self.project_root, "temp", str(exec_user["user_id"]), "support_logs"
        )

        self.helper.ensure_dir_exists(
            os.path.join(self.project_root, "temp", str(exec_user["user_id"]), "zip")
        )
        temp_zip_storage = os.path.join(
            self.project_root, "temp", str(exec_user["user_id"]), "zip"
        )
        os.mkdir(temp_dir)
        temp_zip_storage = os.path.join(temp_zip_storage, "support_logs")
        crafty_path = os.path.join(temp_dir, "crafty")
        os.mkdir(crafty_path)
        server_path = os.path.join(temp_dir, "server")
        os.mkdir(server_path)
        if exec_user["superuser"]:
            defined_servers = self.servers.list_defined_servers()
            user_servers = []
            for server in defined_servers:
                if server not in user_servers:
                    user_servers.append(
                        DatabaseShortcuts.get_data_obj(server.server_object)
                    )
            auth_servers = user_servers
        else:
            defined_servers = self.servers.get_authorized_servers(
                int(exec_user["user_id"])
            )
            user_servers = []
            for server in defined_servers:
                if server not in user_servers:
                    user_servers.append(
                        DatabaseShortcuts.get_data_obj(server.server_object)
                    )
            auth_servers = []
            for server in user_servers:
                if (
                    EnumPermissionsServer.LOGS
                    in self.server_perms.get_user_id_permissions_list(
                        exec_user["user_id"], server["server_id"]
                    )
                ):
                    auth_servers.append(server)
                else:
                    logger.info(
                        f"Logs permission not available for server "
                        f"{server['server_name']}. Skipping."
                    )
        # we'll iterate through our list of log paths from auth servers.
        for server in auth_servers:
            final_path = os.path.join(server_path, str(server["server_name"]))
            try:
                os.mkdir(final_path)
            except FileExistsError:
                final_path += "_" + server["server_uuid"]
                os.mkdir(final_path)
            try:
                FileHelpers.copy_file(
                    pathlib.Path(server["path"], server["log_path"]),
                    final_path,
                )
            except Exception as e:
                logger.warning(f"Failed to copy file with error: {e}")
        # Copy crafty logs to archive dir
        full_log_name = os.path.join(crafty_path, "logs")
        FileHelpers.copy_dir(os.path.join(self.project_root, "logs"), full_log_name)
        self.support_scheduler.add_job(
            self.log_status,
            "interval",
            seconds=1,
            id="logs_" + str(exec_user["user_id"]),
            args=[temp_dir, temp_zip_storage + ".zip", exec_user],
        )
        # Make version file .txt when we download it for support
        # Most people have a default editor for .txt also more mobile friendly...
        sys_info_string = (
            f"Crafty v{self.helper.get_version_string()} Support Logs\n"
            f"\n"
            f"OS Info:- \n"
            f"OS: {str(platform.system())}\n"
            f"Version: {str(platform.release())}"
            f"\n \n"
            f"Log archive created on: {datetime.now()}"
        )
        with open(
            os.path.join(temp_dir, "crafty_sys_info.txt"), "a", encoding="utf-8"
        ) as f:
            f.write(sys_info_string)
        FileHelpers.make_compressed_archive(temp_zip_storage, temp_dir, sys_info_string)
        if len(self.helper.websocket_helper.clients) > 0:
            self.helper.websocket_helper.broadcast_user(
                exec_user["user_id"],
                "support_status_update",
                Helpers.calc_percent(temp_dir, temp_zip_storage + ".zip"),
            )

        temp_zip_storage += ".zip"
        self.helper.websocket_helper.broadcast_user(
            exec_user["user_id"], "send_logs_bootbox", {}
        )

        self.users.set_support_path(exec_user["user_id"], temp_zip_storage)

        self.users.stop_prepare(exec_user["user_id"])
        self.support_scheduler.remove_job("logs_" + str(exec_user["user_id"]))

        FileHelpers.del_dirs(temp_dir)

    def del_support_file(self, temp_zip_storage):
        try:
            FileHelpers.del_file(temp_zip_storage)
            logger.info(
                f"Old support logs successfully deleted from {temp_zip_storage}"
            )
        except FileNotFoundError:
            logger.info("No temp file found. Assuming it's already been cleaned up")
        except PermissionError:
            logger.error("Unable to remove old logs. Permission denied error.")

    def add_system_user(self):
        self.users_helper.add_user(
            "system",
            Helpers.random_string_generator(64),
            "default@example.com",
            False,
            False,
        )

    def log_status(self, source_path, dest_path, exec_user):
        results = Helpers.calc_percent(source_path, dest_path)
        self.log_stats = results

        if len(self.helper.websocket_helper.clients) > 0:
            self.helper.websocket_helper.broadcast_user(
                exec_user["user_id"], "support_status_update", results
            )

    def get_config_diff(self):
        master_config = Helpers.get_master_config()
        try:
            user_config = self.helper.get_all_settings()
        except:
            # Call helper to set updated config.
            Console.warning("No Config found. Setting Default Config.json")
            user_config = master_config
            keys = list(user_config.keys())
            keys.sort()
            sorted_data = {i: user_config[i] for i in keys}
            self.helper.set_settings(user_config)
            return
        items_to_del = []

        # Iterate through user's config.json and check for
        # Keys/values that need to be removed
        for key in user_config:
            if key not in master_config.keys():
                items_to_del.append(key)

        # Remove key/values from user config that were staged
        for item in items_to_del[:]:
            del user_config[item]

        # Add new keys to user config.
        for key, value in master_config.items():
            if key not in user_config.keys():
                user_config[key] = value
        # Call helper to set updated config.
        keys = list(user_config.keys())
        keys.sort()
        sorted_data = {i: user_config[i] for i in keys}
        self.helper.set_settings(sorted_data)

    def send_log_status(self):
        try:
            return self.log_stats
        except:
            return {"percent": 0, "total_files": 0}

    def create_api_server(self, data: dict, user_id):
        server_fs_uuid = Helpers.create_uuid()
        new_server_path = os.path.join(self.helper.servers_dir, server_fs_uuid)
        backup_path = os.path.join(self.helper.backup_path, server_fs_uuid)

        if Helpers.is_os_windows():
            new_server_path = Helpers.wtol_path(new_server_path)
            backup_path = Helpers.wtol_path(backup_path)
            new_server_path.replace(" ", "^ ")
            backup_path.replace(" ", "^ ")

        Helpers.ensure_dir_exists(new_server_path)
        Helpers.ensure_dir_exists(backup_path)

        def _create_server_properties_if_needed(port, empty=False):
            properties_file = os.path.join(new_server_path, "server.properties")
            has_properties = os.path.exists(properties_file)

            if not has_properties:
                logger.info(
                    f"No server.properties found on import."
                    f"Creating one with port selection of {port}"
                )
                with open(
                    properties_file,
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(
                        "# generated by Crafty Controller"
                        + ("" if empty else f"\nserver-port={port}")
                    )

        server_file = "server.jar"  # HACK: Throw this horrible default out of here
        root_create_data = data[data["create_type"] + "_create_data"]
        create_data = root_create_data[root_create_data["create_type"] + "_create_data"]
        if data["create_type"] == "minecraft_java":
            if root_create_data["create_type"] == "download_jar":
                server_file = f"{create_data['type']}-{create_data['version']}.jar"

                # Create an EULA file
                if "agree_to_eula" in create_data:
                    with open(
                        os.path.join(new_server_path, "eula.txt"), "w", encoding="utf-8"
                    ) as file:
                        file.write(
                            "eula="
                            + ("true" if create_data["agree_to_eula"] else "false")
                        )
            elif root_create_data["create_type"] == "import_server":
                server_file = create_data["jarfile"]
            elif root_create_data["create_type"] == "import_zip":
                # TODO: Copy files from the zip file to the new server directory
                server_file = create_data["jarfile"]
                self.import_zip_server()
                raise NotImplementedError("Not yet implemented")
            _create_server_properties_if_needed(
                create_data["server_properties_port"],
            )

            min_mem = create_data["mem_min"]
            max_mem = create_data["mem_max"]

            full_jar_path = os.path.join(new_server_path, server_file)

            def _gibs_to_mibs(gibs: float) -> str:
                return str(int(gibs * 1024))

            def _wrap_jar_if_windows():
                return f'"{server_file}"' if Helpers.is_os_windows() else server_file

            if root_create_data["create_type"] == "download_jar":
                if Helpers.is_os_windows():
                    # Let's check for and setup for install server commands
                    if create_data["type"] == "forge":
                        server_command = (
                            f"java -Xms{Helpers.float_to_string(min_mem)}M "
                            f"-Xmx{Helpers.float_to_string(max_mem)}M "
                            f'-jar "{server_file}" --installServer'
                        )
                    else:
                        server_command = (
                            f"java -Xms{Helpers.float_to_string(min_mem)}M "
                            f"-Xmx{Helpers.float_to_string(max_mem)}M "
                            f'-jar "{server_file}" nogui'
                        )
                else:
                    if create_data["type"] == "forge":
                        server_command = (
                            f"java -Xms{Helpers.float_to_string(min_mem)}M "
                            f"-Xmx{Helpers.float_to_string(max_mem)}M "
                            f"-jar {server_file} --installServer"
                        )
                    else:
                        server_command = (
                            f"java -Xms{Helpers.float_to_string(min_mem)}M "
                            f"-Xmx{Helpers.float_to_string(max_mem)}M "
                            f"-jar {server_file} nogui"
                        )
            else:
                server_command = (
                    f"java -Xms{_gibs_to_mibs(min_mem)}M "
                    f"-Xmx{_gibs_to_mibs(max_mem)}M "
                    f"-jar {_wrap_jar_if_windows()} nogui"
                )

        elif data["create_type"] == "minecraft_bedrock":
            if root_create_data["create_type"] == "import_server":
                existing_server_path = Helpers.get_os_understandable_path(
                    create_data["existing_server_path"]
                )
                if Helpers.is_os_windows():
                    server_command = (
                        f'"{os.path.join(new_server_path, create_data["executable"])}"'
                    )
                else:
                    server_command = f"./{create_data['executable']}"
                logger.debug("command: " + server_command)
            elif root_create_data["create_type"] == "import_zip":
                # TODO: Copy files from the zip file to the new server directory
                raise NotImplementedError("Not yet implemented")

            _create_server_properties_if_needed(0, True)

            server_command = create_data["command"]
            server_file = (
                "./bedrock_server"  # HACK: This is a hack to make the server start
            )
        elif data["create_type"] == "custom":
            # TODO: working_directory, executable_update
            if root_create_data["create_type"] == "raw_exec":
                pass
            elif root_create_data["create_type"] == "import_server":
                existing_server_path = Helpers.get_os_understandable_path(
                    create_data["existing_server_path"]
                )
                try:
                    FileHelpers.copy_dir(existing_server_path, new_server_path, True)
                except shutil.Error as ex:
                    logger.error(f"Server import failed with error: {ex}")
            elif root_create_data["create_type"] == "import_zip":
                # TODO: Copy files from the zip file to the new server directory
                raise NotImplementedError("Not yet implemented")

            _create_server_properties_if_needed(0, True)

            server_command = create_data["command"]

            server_file_new = root_create_data["executable_update"].get("file", "")
            if server_file_new != "":
                # HACK: Horrible hack to make the server start
                server_file = server_file_new

        stop_command = data.get("stop_command", "")
        if stop_command == "":
            # TODO: different default stop commands for server creation types
            stop_command = "stop"

        log_location = data.get("log_location", "")
        if log_location == "" and data["create_type"] == "minecraft_java":
            log_location = "./logs/latest.log"

        if data["monitoring_type"] == "minecraft_java":
            monitoring_port = data["minecraft_java_monitoring_data"]["port"]
            monitoring_host = data["minecraft_java_monitoring_data"]["host"]
            monitoring_type = "minecraft-java"
        elif data["monitoring_type"] == "minecraft_bedrock":
            monitoring_port = data["minecraft_bedrock_monitoring_data"]["port"]
            monitoring_host = data["minecraft_bedrock_monitoring_data"]["host"]
            monitoring_type = "minecraft-bedrock"
        elif data["monitoring_type"] == "none":
            # TODO: this needs to be NUKED..
            # There shouldn't be anything set if there is nothing to monitor
            monitoring_port = 25565
            monitoring_host = "127.0.0.1"
            monitoring_type = "minecraft-java"

        new_server_id = self.register_server(
            name=data["name"],
            server_uuid=server_fs_uuid,
            server_dir=new_server_path,
            backup_path=backup_path,
            server_command=server_command,
            server_file=server_file,
            server_log_file=log_location,
            server_stop=stop_command,
            server_port=monitoring_port,
            created_by=user_id,
            server_host=monitoring_host,
            server_type=monitoring_type,
        )
        if data["create_type"] == "minecraft_java":
            if root_create_data["create_type"] == "download_jar":
                # modded update urls from server jars will only update the installer
                if create_data["category"] != "modded":
                    server_obj = self.servers.get_server_obj(new_server_id)
                    url = (
                        f"https://serverjars.com/api/fetchJar/{create_data['category']}"
                        f"/{create_data['type']}/{create_data['version']}"
                    )
                    server_obj.executable_update_url = url
                    self.servers.update_server(server_obj)
                self.server_jars.download_jar(
                    create_data["category"],
                    create_data["type"],
                    create_data["version"],
                    full_jar_path,
                    new_server_id,
                )
            elif root_create_data["create_type"] == "import_server":
                ServersController.set_import(new_server_id)
                self.import_helper.import_jar_server(
                    create_data["existing_server_path"],
                    os.path.join(new_server_path, server_fs_uuid),
                    monitoring_port,
                    new_server_id,
                )
            elif root_create_data["create_type"] == "import_zip":
                ServersController.set_import(new_server_id)

        elif data["create_type"] == "minecraft-bedrock":
            if root_create_data["create_type"] == "download_executable":
                ServersController.set_import(new_server_id)
                self.import_helper.download_bedrock_server(
                    new_server_path, new_server_id
                )
            elif root_create_data["create_type"] == "import_executable":
                full_exe_path = os.path.join(new_server_path, create_data["executable"])
                self.import_helper.import_bedrock_server(
                    create_data["existing_server_path"],
                    os.path.join(new_server_path, server_fs_uuid),
                    monitoring_port,
                    full_exe_path,
                    new_server_id,
                )
            elif root_create_data["create_type"] == "import_zip":
                full_exe_path = os.path.join(new_server_path, create_data["executable"])
                self.import_helper.import_bedrock_zip_server(
                    create_data["zip_path"],
                    new_server_path,
                    os.path.join(create_data["zip_root"], create_data["executable"]),
                    monitoring_port,
                    new_server_id,
                )

        exec_user = self.users.get_user_by_id(int(user_id))
        captured_roles = data.get("roles", [])
        # These lines create a new Role for the Server with full permissions
        # and add the user to it if he's not a superuser
        if len(captured_roles) == 0:
            if not exec_user["superuser"]:
                new_server_uuid = self.servers.get_server_data_by_id(new_server_id).get(
                    "server_uuid"
                )
                role_id = self.roles.add_role(
                    f"Creator of Server with uuid={new_server_uuid}",
                    exec_user["user_id"],
                )
                self.server_perms.add_role_server(new_server_id, role_id, "11111111")
                self.users.add_role_to_user(exec_user["user_id"], role_id)

        else:
            for role in captured_roles:
                role_id = role
                self.server_perms.add_role_server(new_server_id, role_id, "11111111")

        return new_server_id, server_fs_uuid

    @staticmethod
    def verify_jar_server(server_path: str, server_jar: str):
        server_path = Helpers.get_os_understandable_path(server_path)
        path_check = Helpers.check_path_exists(server_path)
        jar_check = Helpers.check_file_exists(os.path.join(server_path, server_jar))
        if not path_check or not jar_check:
            return False
        return True

    @staticmethod
    def verify_zip_server(zip_path: str):
        zip_path = Helpers.get_os_understandable_path(zip_path)
        zip_check = Helpers.check_file_exists(zip_path)
        if not zip_check:
            return False
        return True

    # **********************************************************************************
    #                                   BEDROCK IMPORTS
    # **********************************************************************************

    def import_bedrock_server(
        self,
        server_name: str,
        server_path: str,
        server_exe: str,
        port: int,
        user_id: int,
    ):
        server_id = Helpers.create_uuid()
        new_server_dir = os.path.join(self.helper.servers_dir, server_id)
        backup_path = os.path.join(self.helper.backup_path, server_id)
        if Helpers.is_os_windows():
            new_server_dir = Helpers.wtol_path(new_server_dir)
            backup_path = Helpers.wtol_path(backup_path)
            new_server_dir.replace(" ", "^ ")
            backup_path.replace(" ", "^ ")

        Helpers.ensure_dir_exists(new_server_dir)
        Helpers.ensure_dir_exists(backup_path)
        server_path = Helpers.get_os_understandable_path(server_path)

        full_jar_path = os.path.join(new_server_dir, server_exe)

        if Helpers.is_os_windows():
            server_command = f'"{full_jar_path}"'
        else:
            server_command = f"./{server_exe}"
        logger.debug("command: " + server_command)
        server_log_file = ""
        server_stop = "stop"

        new_id = self.register_server(
            server_name,
            server_id,
            new_server_dir,
            backup_path,
            server_command,
            server_exe,
            server_log_file,
            server_stop,
            port,
            user_id,
            server_type="minecraft-bedrock",
        )
        ServersController.set_import(new_id)
        self.import_helper.import_bedrock_server(
            server_path, new_server_dir, port, full_jar_path, new_id
        )
        return new_id

    def create_bedrock_server(self, server_name, user_id):
        server_id = Helpers.create_uuid()
        new_server_dir = os.path.join(self.helper.servers_dir, server_id)
        backup_path = os.path.join(self.helper.backup_path, server_id)
        server_exe = "bedrock_server"
        if Helpers.is_os_windows():
            # if this is windows we will override the linux bedrock server name.
            server_exe = "bedrock_server.exe"
            new_server_dir = Helpers.wtol_path(new_server_dir)
            backup_path = Helpers.wtol_path(backup_path)
            new_server_dir.replace(" ", "^ ")
            backup_path.replace(" ", "^ ")

        Helpers.ensure_dir_exists(new_server_dir)
        Helpers.ensure_dir_exists(backup_path)

        full_jar_path = os.path.join(new_server_dir, server_exe)

        if Helpers.is_os_windows():
            server_command = f'"{full_jar_path}"'
        else:
            server_command = f"./{server_exe}"
        logger.debug("command: " + server_command)
        server_log_file = ""
        server_stop = "stop"

        new_id = self.register_server(
            server_name,
            server_id,
            new_server_dir,
            backup_path,
            server_command,
            server_exe,
            server_log_file,
            server_stop,
            "19132",
            user_id,
            server_type="minecraft-bedrock",
        )
        ServersController.set_import(new_id)
        self.import_helper.download_bedrock_server(new_server_dir, new_id)
        return new_id

    def import_bedrock_zip_server(
        self,
        server_name: str,
        zip_path: str,
        server_exe: str,
        port: int,
        user_id: int,
    ):
        server_id = Helpers.create_uuid()
        new_server_dir = os.path.join(self.helper.servers_dir, server_id)
        backup_path = os.path.join(self.helper.backup_path, server_id)
        if Helpers.is_os_windows():
            new_server_dir = Helpers.wtol_path(new_server_dir)
            backup_path = Helpers.wtol_path(backup_path)
            new_server_dir.replace(" ", "^ ")
            backup_path.replace(" ", "^ ")

        temp_dir = Helpers.get_os_understandable_path(zip_path)
        Helpers.ensure_dir_exists(new_server_dir)
        Helpers.ensure_dir_exists(backup_path)

        full_jar_path = os.path.join(new_server_dir, server_exe)

        if Helpers.is_os_windows():
            server_command = f'"{full_jar_path}"'
        else:
            server_command = f"./{server_exe}"
        logger.debug("command: " + server_command)
        server_log_file = ""
        server_stop = "stop"

        new_id = self.register_server(
            server_name,
            server_id,
            new_server_dir,
            backup_path,
            server_command,
            server_exe,
            server_log_file,
            server_stop,
            port,
            user_id,
            server_type="minecraft-bedrock",
        )
        ServersController.set_import(new_id)
        self.import_helper.import_bedrock_zip_server(
            temp_dir, new_server_dir, full_jar_path, port, new_id
        )
        if os.name != "nt":
            if Helpers.check_file_exists(full_jar_path):
                os.chmod(full_jar_path, 0o2760)

        return new_id

    # **********************************************************************************
    #                                   BEDROCK IMPORTS END
    # **********************************************************************************

    def rename_backup_dir(self, old_server_id, new_server_id, new_uuid):
        server_data = self.servers.get_server_data_by_id(old_server_id)
        server_obj = self.servers.get_server_obj(new_server_id)
        old_bu_path = server_data["backup_path"]
        ServerPermsController.backup_role_swap(old_server_id, new_server_id)
        backup_path = old_bu_path
        backup_path = Path(backup_path)
        backup_path_components = list(backup_path.parts)
        backup_path_components[-1] = new_uuid
        new_bu_path = pathlib.PurePath(os.path.join(*backup_path_components))
        server_obj.backup_path = new_bu_path
        default_backup_dir = os.path.join(self.helper.backup_path, new_uuid)
        try:
            os.rmdir(default_backup_dir)
        except:
            logger.error("Could not delete default backup dir")
        self.servers.update_server(server_obj)
        backup_path.rename(new_bu_path)

    def register_server(
        self,
        name: str,
        server_uuid: str,
        server_dir: str,
        backup_path: str,
        server_command: str,
        server_file: str,
        server_log_file: str,
        server_stop: str,
        server_port: int,
        created_by: int,
        server_type: str,
        server_host: str = "127.0.0.1",
    ):
        # put data in the db
        new_id = self.servers.create_server(
            name,
            server_uuid,
            server_dir,
            backup_path,
            server_command,
            server_file,
            server_log_file,
            server_stop,
            server_type,
            created_by,
            server_port,
            server_host,
        )

        if not Helpers.check_file_exists(
            os.path.join(server_dir, "crafty_managed.txt")
        ):
            try:
                # place a file in the dir saying it's owned by crafty
                with open(
                    os.path.join(server_dir, "crafty_managed.txt"),
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(
                        "The server is managed by Crafty Controller.\n "
                        "Leave this directory/files alone please"
                    )

            except Exception as e:
                logger.error(f"Unable to create required server files due to :{e}")
                return False

        # let's re-init all servers
        self.servers.init_all_servers()

        return new_id

    def remove_server(self, server_id, files):
        counter = 0
        for server in self.servers.servers_list:
            # if this is the droid... im mean server we are looking for...
            if str(server["server_id"]) == str(server_id):
                server_data = self.servers.get_server_data(server_id)
                server_name = server_data["server_name"]

                logger.info(f"Deleting Server: ID {server_id} | Name: {server_name} ")
                Console.info(f"Deleting Server: ID {server_id} | Name: {server_name} ")

                srv_obj = server["server_obj"]
                srv_obj.server_scheduler.shutdown()
                running = srv_obj.check_running()

                if running:
                    self.servers.stop_server(server_id)
                if files:
                    try:
                        FileHelpers.del_dirs(
                            Helpers.get_os_understandable_path(
                                self.servers.get_server_data_by_id(server_id)["path"]
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f"Unable to delete server files for server with ID: "
                            f"{server_id} with error logged: {e}"
                        )
                    if Helpers.check_path_exists(
                        self.servers.get_server_data_by_id(server_id)["backup_path"]
                    ):
                        FileHelpers.del_dirs(
                            Helpers.get_os_understandable_path(
                                self.servers.get_server_data_by_id(server_id)[
                                    "backup_path"
                                ]
                            )
                        )

                # Cleanup scheduled tasks
                try:
                    HelpersManagement.delete_scheduled_task_by_server(server_id)
                except DoesNotExist:
                    logger.info("No scheduled jobs exist. Continuing.")
                # remove the server from the DB
                self.servers.remove_server(server_id)

                # remove the server from servers list
                self.servers.servers_list.pop(counter)

            counter += 1

    def remove_unloaded_server(self, server_id):
        try:
            HelpersManagement.delete_scheduled_task_by_server(server_id)
        except DoesNotExist:
            logger.info("No scheduled jobs exist. Continuing.")
        # remove the server from the DB
        self.servers.remove_server(server_id)

    @staticmethod
    def clear_support_status():
        HelperUsers.clear_support_status()

    def set_master_server_dir(self, server_dir):
        # This method should only be used on a first run basis if the server dir is ""
        self.helper.servers_dir = server_dir
        HelpersManagement.set_master_server_dir(server_dir)

    def update_master_server_dir(self, server_dir, user_id):
        self.helper.dir_migration = True
        move_thread = threading.Thread(
            name="dir_move",
            target=self.t_update_master_server_dir,
            daemon=True,
            args=(
                server_dir,
                user_id,
            ),
        )
        move_thread.start()

    def t_update_master_server_dir(self, new_server_path, user_id):
        new_server_path = self.helper.wtol_path(new_server_path)
        new_server_path = os.path.join(new_server_path, "servers")
        self.helper.websocket_helper.broadcast_page(
            "/panel/panel_config", "move_status", "Checking dir"
        )
        current_master = self.helper.wtol_path(
            HelpersManagement.get_master_server_dir()
        )
        if current_master == new_server_path:
            logger.info(
                "Admin tried to change server dir to current server dir. Canceling..."
            )
            self.helper.websocket_helper.broadcast_page(
                "/panel/panel_config",
                "move_status",
                "done",
            )
            return
        if self.helper.is_subdir(new_server_path, current_master):
            logger.info(
                "Admin tried to change server dir to be inside a sub directory of the"
                " current server dir. This will result in a copy loop."
            )
            self.helper.websocket_helper.broadcast_page(
                "/panel/panel_config",
                "move_status",
                "done",
            )
            return

        self.helper.websocket_helper.broadcast_page(
            "/panel/panel_config", "move_status", "Checking permissions"
        )
        if not self.helper.ensure_dir_exists(new_server_path):
            self.helper.websocket_helper.broadcast_user(
                user_id,
                "send_start_error",
                {
                    "error": "Crafty failed to move server dir. "
                    "It seems Crafty lacks permission to write to "
                    "the new directory."
                },
            )
            return
        # set the cached serve dir
        self.helper.servers_dir = new_server_path
        # set DB server dir
        HelpersManagement.set_master_server_dir(new_server_path)
        servers = self.servers.get_all_defined_servers()
        # move the servers
        for server in servers:
            server_path = server.get("path")
            new_local_server_path = os.path.join(
                new_server_path, server.get("server_uuid")
            )
            if os.path.isdir(server_path):
                self.helper.websocket_helper.broadcast_page(
                    "/panel/panel_config",
                    "move_status",
                    f"Moving {server.get('server_name')}",
                )
                try:
                    self.file_helper.move_dir(
                        server_path,
                        new_local_server_path,
                    )
                except FileExistsError as e:
                    logger.error(f"Failed to move server with error: {e}")

            server_obj = self.servers.get_server_obj(server.get("server_id"))

            # reset executable path
            if current_master in server["executable"]:
                server_obj.executable = str(server["executable"]).replace(
                    current_master, new_local_server_path
                )
            # reset run command path
            if current_master in server["execution_command"]:
                server_obj.execution_command = str(server["execution_command"]).replace(
                    current_master, new_local_server_path
                )
            # reset log path
            if current_master in server["log_path"]:
                server_obj.log_path = str(server["log_path"]).replace(
                    current_master, new_local_server_path
                )
            server_obj.path = new_local_server_path
            failed = False
            for s in self.servers.failed_servers:
                if int(s["server_id"]) == int(server.get("server_id")):
                    failed = True
            if not failed:
                self.servers.update_server(server_obj)
            else:
                self.servers.update_unloaded_server(server_obj)
        self.servers.init_all_servers()
        self.helper.dir_migration = False
        self.helper.websocket_helper.broadcast_page(
            "/panel/panel_config",
            "move_status",
            "done",
        )

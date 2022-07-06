# pylint: disable=too-many-lines
import time
import datetime
import os
import typing as t
import json
import logging
import threading
import shlex
import bleach
import libgravatar
import requests
import tornado.web
import tornado.escape
from tornado import iostream

# TZLocal is set as a hidden import on win pipeline
from tzlocal import get_localzone
from tzlocal.utils import ZoneInfoNotFoundError
from croniter import croniter

from app.classes.models.servers import Servers
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.models.management import HelpersManagement
from app.classes.controllers.roles_controller import RolesController
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class PanelHandler(BaseHandler):
    def get_user_roles(self) -> t.Dict[str, list]:
        user_roles = {}
        for user_id in self.controller.users.get_all_user_ids():
            user_roles_list = self.controller.users.get_user_roles_names(user_id)
            # user_servers =
            # self.controller.servers.get_authorized_servers(user.user_id)
            user_roles[user_id] = user_roles_list
        return user_roles

    def get_role_servers(self) -> t.List[RolesController.RoleServerJsonType]:
        servers = []
        for server in self.controller.servers.get_all_defined_servers():
            argument = self.get_argument(f"server_{server['server_id']}_access", "0")
            if argument == "0":
                continue

            permission_mask = "0" * len(EnumPermissionsServer)
            for permission in self.controller.server_perms.list_defined_permissions():
                argument = self.get_argument(
                    f"permission_{server['server_id']}_{permission.name}", "0"
                )
                if argument == "1":
                    permission_mask = self.controller.server_perms.set_permission(
                        permission_mask, permission, "1"
                    )

            servers.append(
                {"server_id": server["server_id"], "permissions": permission_mask}
            )
        return servers

    def get_perms_quantity(self) -> t.Tuple[str, dict]:
        permissions_mask: str = "000"
        server_quantity: dict = {}
        for (
            permission
        ) in self.controller.crafty_perms.list_defined_crafty_permissions():
            argument = int(
                float(
                    bleach.clean(
                        self.get_argument(f"permission_{permission.name}", "0")
                    )
                )
            )
            if argument:
                permissions_mask = self.controller.crafty_perms.set_permission(
                    permissions_mask, permission, argument
                )

            q_argument = int(
                float(
                    bleach.clean(self.get_argument(f"quantity_{permission.name}", "0"))
                )
            )
            if q_argument:
                server_quantity[permission.name] = q_argument
            else:
                server_quantity[permission.name] = 0
        return permissions_mask, server_quantity

    def get_perms(self) -> str:
        permissions_mask: str = "000"
        for (
            permission
        ) in self.controller.crafty_perms.list_defined_crafty_permissions():
            argument = self.get_argument(f"permission_{permission.name}", None)
            if argument is not None and argument == "1":
                permissions_mask = self.controller.crafty_perms.set_permission(
                    permissions_mask, permission, "1"
                )
        return permissions_mask

    def get_perms_server(self) -> str:
        permissions_mask: str = "00000000"
        for permission in self.controller.server_perms.list_defined_permissions():
            argument = self.get_argument(f"permission_{permission.name}", None)
            if argument is not None:
                permissions_mask = self.controller.server_perms.set_permission(
                    permissions_mask, permission, 1 if argument == "1" else 0
                )
        return permissions_mask

    def get_user_role_memberships(self) -> set:
        roles = set()
        for role in self.controller.roles.get_all_roles():
            if self.get_argument(f"role_{role.role_id}_membership", None) == "1":
                roles.add(role.role_id)
        return roles

    def download_file(self, name: str, file: str):
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", f"attachment; filename={name}")
        chunk_size = 1024 * 1024 * 4  # 4 MiB

        with open(file, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                try:
                    self.write(chunk)  # write the chunk to response
                    self.flush()  # send the chunk to client
                except iostream.StreamClosedError:
                    # this means the client has closed the connection
                    # so break the loop
                    break
                finally:
                    # deleting the chunk is very important because
                    # if many clients are downloading files at the
                    # same time, the chunks in memory will keep
                    # increasing and will eat up the RAM
                    del chunk

    def check_server_id(self):
        server_id = self.get_argument("id", None)

        api_key, _, exec_user = self.current_user
        superuser = exec_user["superuser"]

        # Commented out because there is no server access control for API keys,
        # they just inherit from the host user
        # if api_key is not None:
        #     superuser = superuser and api_key.superuser

        if server_id is None:
            self.redirect("/panel/error?error=Invalid Server ID")
            return None
        # Does this server exist?
        if not self.controller.servers.server_id_exists(server_id):
            self.redirect("/panel/error?error=Invalid Server ID")
            return None

        # Does the user have permission?
        if superuser:  # TODO: Figure out a better solution
            return server_id
        if api_key is not None:
            if not self.controller.servers.server_id_authorized_api_key(
                server_id, api_key
            ):
                logger.debug(
                    f"API key {api_key.name} (id: {api_key.token_id}) "
                    f"does not have permission"
                )
                self.redirect("/panel/error?error=Invalid Server ID")
                return None
        else:
            if not self.controller.servers.server_id_authorized(
                server_id, exec_user["user_id"]
            ):
                logger.debug(f'User {exec_user["user_id"]} does not have permission')
                self.redirect("/panel/error?error=Invalid Server ID")
                return None
        return server_id

    # Server fetching, spawned asynchronously
    # TODO: Make the related front-end elements update with AJAX
    def fetch_server_data(self, page_data):
        total_players = 0
        for server in page_data["servers"]:
            total_players += len(
                self.controller.servers.stats.get_server_players(
                    server["server_data"]["server_id"]
                )
            )
        page_data["num_players"] = total_players

        for server in page_data["servers"]:
            try:
                data = json.loads(server["int_ping_results"])
                server["int_ping_results"] = data
            except Exception as e:
                logger.error(f"Failed server data for page with error: {e}")

        return page_data

    @tornado.web.authenticated
    async def get(self, page):
        error = self.get_argument("error", "WTF Error!")

        template = "panel/denied.html"

        now = time.time()
        formatted_time = str(
            datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        )

        api_key, _token_data, exec_user = self.current_user
        superuser = exec_user["superuser"]
        if api_key is not None:
            superuser = superuser and api_key.superuser

        if superuser:  # TODO: Figure out a better solution
            defined_servers = self.controller.servers.list_defined_servers()
            exec_user_role = {"Super User"}
            exec_user_crafty_permissions = (
                self.controller.crafty_perms.list_defined_crafty_permissions()
            )
        else:
            if api_key is not None:
                exec_user_crafty_permissions = (
                    self.controller.crafty_perms.get_api_key_permissions_list(api_key)
                )
            else:
                exec_user_crafty_permissions = (
                    self.controller.crafty_perms.get_crafty_permissions_list(
                        exec_user["user_id"]
                    )
                )
            logger.debug(exec_user["roles"])
            exec_user_role = set()
            for r in exec_user["roles"]:
                role = self.controller.roles.get_role(r)
                exec_user_role.add(role["role_name"])
            defined_servers = self.controller.servers.get_authorized_servers(
                exec_user["user_id"]
            )

        user_order = self.controller.users.get_user_by_id(exec_user["user_id"])
        user_order = user_order["server_order"].split(",")
        page_servers = []
        server_ids = []

        for server_id in user_order[:]:
            for server in defined_servers[:]:
                if str(server.server_id) == str(server_id):
                    page_servers.append(
                        DatabaseShortcuts.get_data_obj(server.server_object)
                    )
                    user_order.remove(server_id)
                    defined_servers.remove(server)

        for server in defined_servers:
            server_ids.append(str(server.server_id))
            if server not in page_servers:
                page_servers.append(
                    DatabaseShortcuts.get_data_obj(server.server_object)
                )

        for server_id in user_order[:]:
            # remove IDs in list that user no longer has access to
            if str(server_id) not in server_ids:
                user_order.remove(server_id)
        defined_servers = page_servers

        try:
            tz = get_localzone()
        except ZoneInfoNotFoundError:
            logger.error(
                "Could not capture time zone from system. Falling back to Europe/London"
            )
            tz = "Europe/London"

        page_data: t.Dict[str, t.Any] = {
            # todo: make this actually pull and compare version data
            "update_available": False,
            "serverTZ": tz,
            "version_data": self.helper.get_version_string(),
            "user_data": exec_user,
            "user_role": exec_user_role,
            "user_crafty_permissions": exec_user_crafty_permissions,
            "crafty_permissions": {
                "Server_Creation": EnumPermissionsCrafty.SERVER_CREATION,
                "User_Config": EnumPermissionsCrafty.USER_CONFIG,
                "Roles_Config": EnumPermissionsCrafty.ROLES_CONFIG,
            },
            "server_stats": {
                "total": len(defined_servers),
                "running": len(self.controller.servers.list_running_servers()),
                "stopped": (
                    len(self.controller.servers.list_defined_servers())
                    - len(self.controller.servers.list_running_servers())
                ),
            },
            "menu_servers": defined_servers,
            "hosts_data": self.controller.management.get_latest_hosts_stats(),
            "show_contribute": self.helper.get_setting("show_contribute_link", True),
            "error": error,
            "time": formatted_time,
            "lang": self.controller.users.get_user_lang_by_id(exec_user["user_id"]),
            "lang_page": Helpers.get_lang_page(
                self.controller.users.get_user_lang_by_id(exec_user["user_id"])
            ),
            "super_user": superuser,
            "api_key": {
                "name": api_key.name,
                "created": api_key.created,
                "server_permissions": api_key.server_permissions,
                "crafty_permissions": api_key.crafty_permissions,
                "superuser": api_key.superuser,
            }
            if api_key is not None
            else None,
            "superuser": superuser,
        }

        # http://en.gravatar.com/site/implement/images/#rating
        if self.helper.get_setting("allow_nsfw_profile_pictures"):
            rating = "x"
        else:
            rating = "g"

        # Get grvatar hash for profile pictures
        if exec_user["email"] != "default@example.com" or "":
            gravatar = libgravatar.Gravatar(
                libgravatar.sanitize_email(exec_user["email"])
            )
            url = gravatar.get_image(
                size=80,
                default="404",
                force_default=False,
                rating=rating,
                filetype_extension=False,
                use_ssl=True,
            )  # + "?d=404"
            try:
                if requests.head(url).status_code != 404:
                    profile_url = url
                else:
                    profile_url = "/static/assets/images/faces-clipart/pic-3.png"
            except:
                profile_url = "/static/assets/images/faces-clipart/pic-3.png"
        else:
            profile_url = "/static/assets/images/faces-clipart/pic-3.png"

        page_data["user_image"] = profile_url

        if page == "unauthorized":
            template = "panel/denied.html"

        elif page == "error":
            template = "public/error.html"

        elif page == "credits":
            with open(
                self.helper.credits_cache, encoding="utf-8"
            ) as credits_default_local:
                try:
                    remote = requests.get(
                        "https://craftycontrol.com/credits", allow_redirects=True
                    )
                    credits_dict: dict = remote.json()
                    if not credits_dict["staff"]:
                        logger.error("Issue with upstream Staff, using local.")
                        credits_dict: dict = json.load(credits_default_local)
                except:
                    logger.error("Request to credits bucket failed, using local.")
                    credits_dict: dict = json.load(credits_default_local)

                timestamp = credits_dict["lastUpdate"] / 1000.0
                page_data["patrons"] = credits_dict["patrons"]
                page_data["staff"] = credits_dict["staff"]

                # Filter Language keys to exclude joke prefix '*'
                clean_dict = {
                    user.replace("*", ""): translation
                    for user, translation in credits_dict["translations"].items()
                }
                page_data["translations"] = clean_dict

                # 0 Defines if we are using local credits file andd displays sadcat.
                if timestamp == 0:
                    page_data["lastUpdate"] = "😿"
                else:
                    page_data["lastUpdate"] = str(
                        datetime.datetime.fromtimestamp(timestamp).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )
            template = "panel/credits.html"

        elif page == "contribute":
            template = "panel/contribute.html"

        elif page == "dashboard":
            page_data["first_log"] = self.controller.first_login
            if self.controller.first_login and exec_user["username"] == "admin":
                self.controller.first_login = False
            if superuser:  # TODO: Figure out a better solution
                try:
                    page_data[
                        "servers"
                    ] = self.controller.servers.get_all_servers_stats()
                except IndexError:
                    self.controller.servers.stats.record_stats()
                    page_data[
                        "servers"
                    ] = self.controller.servers.get_all_servers_stats()
            else:
                try:
                    user_auth = self.controller.servers.get_authorized_servers_stats(
                        exec_user["user_id"]
                    )
                except IndexError:
                    self.controller.servers.stats.record_stats()
                    user_auth = self.controller.servers.get_authorized_servers_stats(
                        exec_user["user_id"]
                    )
                logger.debug(f"ASFR: {user_auth}")
                page_data["servers"] = user_auth
                page_data["server_stats"]["running"] = len(
                    list(filter(lambda x: x["stats"]["running"], page_data["servers"]))
                )
                page_data["server_stats"]["stopped"] = (
                    len(page_data["servers"]) - page_data["server_stats"]["running"]
                )

            # set user server order
            user_order = self.controller.users.get_user_by_id(exec_user["user_id"])
            user_order = user_order["server_order"].split(",")
            page_servers = []
            server_ids = []
            un_used_servers = page_data["servers"]
            flag = 0
            for server_id in user_order[:]:
                for server in un_used_servers[:]:
                    if flag == 0:
                        server["stats"][
                            "downloading"
                        ] = self.controller.servers.get_download_status(
                            str(server["stats"]["server_id"]["server_id"])
                        )
                        server["stats"]["crashed"] = self.controller.servers.is_crashed(
                            str(server["stats"]["server_id"]["server_id"])
                        )
                        try:
                            server["stats"][
                                "waiting_start"
                            ] = self.controller.servers.get_waiting_start(
                                str(server["stats"]["server_id"]["server_id"])
                            )
                        except Exception as e:
                            logger.error(f"Failed to get server waiting to start: {e}")
                            server["stats"]["waiting_start"] = False

                    if str(server["server_data"]["server_id"]) == str(server_id):
                        page_servers.append(server)
                        un_used_servers.remove(server)
                        user_order.remove(server_id)
                # we only want to set these server stats values once.
                # We need to update the flag so it only hits that if once.
                flag += 1

            for server in un_used_servers:
                server_ids.append(str(server["server_data"]["server_id"]))
                if server not in page_servers:
                    page_servers.append(server)
            for server_id in user_order:
                # remove IDs in list that user no longer has access to
                if str(server_id) not in server_ids[:]:
                    user_order.remove(server_id)
            page_data["servers"] = page_servers
            for server in page_data["servers"]:
                server_obj = self.controller.servers.get_server_instance_by_id(
                    server["server_data"]["server_id"]
                )
                alert = False
                if server_obj.last_backup_status():
                    alert = True
                server["alert"] = alert

            # num players is set to zero here. If we poll all servers while
            # dashboard is loading it takes FOREVER. We leave this to the
            # async polling once dashboard is served.
            page_data["num_players"] = 0

            template = "panel/dashboard.html"

        elif page == "server_detail":
            subpage = bleach.clean(self.get_argument("subpage", ""))

            server_id = self.check_server_id()
            if server_id is None:
                return

            server_obj = self.controller.servers.get_server_instance_by_id(server_id)
            page_data["backup_failed"] = server_obj.last_backup_status()
            server_obj = None

            valid_subpages = [
                "term",
                "logs",
                "backup",
                "config",
                "files",
                "admin_controls",
                "schedules",
            ]

            server = self.controller.servers.get_server_instance_by_id(server_id)
            # server_data isn't needed since the server_stats also pulls server data
            page_data["server_data"] = self.controller.servers.get_server_data_by_id(
                server_id
            )
            page_data["server_stats"] = self.controller.servers.get_server_stats_by_id(
                server_id
            )
            page_data["downloading"] = self.controller.servers.get_download_status(
                server_id
            )
            try:
                page_data["waiting_start"] = self.controller.servers.get_waiting_start(
                    server_id
                )
            except Exception as e:
                logger.error(f"Failed to get server waiting to start: {e}")
                page_data["waiting_start"] = False
            page_data[
                "get_players"
            ] = lambda: self.controller.servers.stats.get_server_players(server_id)
            page_data["active_link"] = subpage
            page_data["permissions"] = {
                "Commands": EnumPermissionsServer.COMMANDS,
                "Terminal": EnumPermissionsServer.TERMINAL,
                "Logs": EnumPermissionsServer.LOGS,
                "Schedule": EnumPermissionsServer.SCHEDULE,
                "Backup": EnumPermissionsServer.BACKUP,
                "Files": EnumPermissionsServer.FILES,
                "Config": EnumPermissionsServer.CONFIG,
                "Players": EnumPermissionsServer.PLAYERS,
            }
            page_data[
                "user_permissions"
            ] = self.controller.server_perms.get_user_id_permissions_list(
                exec_user["user_id"], server_id
            )
            page_data["server_stats"]["crashed"] = self.controller.servers.is_crashed(
                server_id
            )
            page_data["server_stats"][
                "server_type"
            ] = self.controller.servers.get_server_type_by_id(server_id)
            if subpage not in valid_subpages:
                logger.debug("not a valid subpage")
            if not subpage:
                if (
                    page_data["permissions"]["Terminal"]
                    in page_data["user_permissions"]
                ):
                    subpage = "term"
                elif page_data["permissions"]["Logs"] in page_data["user_permissions"]:
                    subpage = "logs"
                elif (
                    page_data["permissions"]["Schedule"]
                    in page_data["user_permissions"]
                ):
                    subpage = "schedules"
                elif (
                    page_data["permissions"]["Backup"] in page_data["user_permissions"]
                ):
                    subpage = "backup"
                elif page_data["permissions"]["Files"] in page_data["user_permissions"]:
                    subpage = "files"
                elif (
                    page_data["permissions"]["Config"] in page_data["user_permissions"]
                ):
                    subpage = "config"
                elif (
                    page_data["permissions"]["Players"] in page_data["user_permissions"]
                ):
                    subpage = "admin_controls"
                else:
                    self.redirect("/panel/error?error=Unauthorized access to Server")
            logger.debug(f'Subpage: "{subpage}"')

            if subpage == "term":
                if (
                    not page_data["permissions"]["Terminal"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect(
                            "/panel/error?error=Unauthorized access to Terminal"
                        )
                        return

            if subpage == "logs":
                if (
                    not page_data["permissions"]["Logs"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect("/panel/error?error=Unauthorized access to Logs")
                        return

            if subpage == "schedules":
                if (
                    not page_data["permissions"]["Schedule"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect(
                            "/panel/error?error=Unauthorized access To Schedules"
                        )
                        return
                page_data["schedules"] = HelpersManagement.get_schedules_by_server(
                    server_id
                )

            if subpage == "config":
                if (
                    not page_data["permissions"]["Config"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect(
                            "/panel/error?error=Unauthorized access Server Config"
                        )
                        return
                page_data["java_versions"] = Helpers.find_java_installs()
                server_obj: Servers = self.controller.servers.get_server_obj(server_id)
                page_java = []
                page_data["java_versions"].append("java")
                for version in page_data["java_versions"]:
                    if os.name == "nt":
                        page_java.append(version)
                    else:
                        if len(version) > 0:
                            page_java.append(version)

                page_data["java_versions"] = page_java

            if subpage == "files":
                if (
                    not page_data["permissions"]["Files"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect("/panel/error?error=Unauthorized access Files")
                        return

            if subpage == "backup":
                if (
                    not page_data["permissions"]["Backup"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect(
                            "/panel/error?error=Unauthorized access to Backups"
                        )
                        return
                server_info = self.controller.servers.get_server_data_by_id(server_id)
                page_data[
                    "backup_config"
                ] = self.controller.management.get_backup_config(server_id)
                exclusions = []
                page_data[
                    "exclusions"
                ] = self.controller.management.get_excluded_backup_dirs(server_id)
                page_data[
                    "backing_up"
                ] = self.controller.servers.get_server_instance_by_id(
                    server_id
                ).is_backingup
                page_data[
                    "backup_stats"
                ] = self.controller.servers.get_server_instance_by_id(
                    server_id
                ).send_backup_status()
                # makes it so relative path is the only thing shown
                for file in page_data["exclusions"]:
                    if Helpers.is_os_windows():
                        exclusions.append(file.replace(server_info["path"] + "\\", ""))
                    else:
                        exclusions.append(file.replace(server_info["path"] + "/", ""))
                page_data["exclusions"] = exclusions
                self.controller.servers.refresh_server_settings(server_id)
                try:
                    page_data["backup_list"] = server.list_backups()
                except:
                    page_data["backup_list"] = []
                page_data["backup_path"] = Helpers.wtol_path(server_info["backup_path"])

            def get_banned_players_html():
                banned_players = self.controller.servers.get_banned_players(server_id)
                if banned_players is None:
                    return """
                    <li class="playerItem banned">
                        <h3>Error while reading banned-players.json</h3>
                    </li>
                    """
                html = ""
                for player in banned_players:
                    html += f"""
                    <li class="playerItem banned">
                        <h3>{player['name']}</h3>
                        <span>Banned by {player['source']} for reason: {player['reason']}</span>
                        <button onclick="send_command_to_server('pardon {player['name']}')" type="button" class="btn btn-danger">Unban</button>
                    </li>
                    """

                return html

            if subpage == "admin_controls":
                if (
                    not page_data["permissions"]["Players"]
                    in page_data["user_permissions"]
                ):
                    if not superuser:
                        self.redirect("/panel/error?error=Unauthorized access")
                page_data["banned_players"] = get_banned_players_html()

            template = f"panel/server_{subpage}.html"

        elif page == "download_backup":
            file = self.get_argument("file", "")

            server_id = self.check_server_id()
            if server_id is None:
                return

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            backup_file = os.path.abspath(
                os.path.join(
                    Helpers.get_os_understandable_path(server_info["backup_path"]), file
                )
            )
            if not Helpers.in_path(
                Helpers.get_os_understandable_path(server_info["backup_path"]),
                backup_file,
            ) or not os.path.isfile(backup_file):
                self.redirect("/panel/error?error=Invalid path detected")
                return

            self.download_file(file, backup_file)

            self.redirect(f"/panel/server_detail?id={server_id}&subpage=backup")

        elif page == "panel_config":
            auth_servers = {}
            auth_role_servers = {}
            roles = self.controller.roles.get_all_roles()
            user_roles = {}
            for user in self.controller.users.get_all_users():
                user_roles_list = self.controller.users.get_user_roles_names(
                    user.user_id
                )
                user_servers = self.controller.servers.get_authorized_servers(
                    user.user_id
                )
                servers = []
                for server in user_servers:
                    if server.name not in servers:
                        servers.append(server.name)
                new_item = {user.user_id: servers}
                auth_servers.update(new_item)
                data = {user.user_id: user_roles_list}
                user_roles.update(data)
            for role in roles:
                role_servers = []
                role = self.controller.roles.get_role_with_servers(role.role_id)
                for serv_id in role["servers"]:
                    role_servers.append(
                        self.controller.servers.get_server_data_by_id(serv_id)[
                            "server_name"
                        ]
                    )
                data = {role["role_id"]: role_servers}
                auth_role_servers.update(data)

            page_data["auth-servers"] = auth_servers
            page_data["role-servers"] = auth_role_servers
            page_data["user-roles"] = user_roles

            page_data["users"] = self.controller.users.user_query(exec_user["user_id"])
            page_data["roles"] = self.controller.users.user_role_query(
                exec_user["user_id"]
            )

            for user in page_data["users"]:
                if user.user_id != exec_user["user_id"]:
                    user.api_token = "********"
            if superuser:
                for user in self.controller.users.get_all_users():
                    if user.superuser:
                        super_auth_servers = ["Super User Access To All Servers"]
                        page_data["users"] = self.controller.users.get_all_users()
                        page_data["roles"] = self.controller.roles.get_all_roles()
                        page_data["auth-servers"][user.user_id] = super_auth_servers

            template = "panel/panel_config.html"

        elif page == "add_user":
            page_data["new_user"] = True
            page_data["user"] = {}
            page_data["user"]["username"] = ""
            page_data["user"]["user_id"] = -1
            page_data["user"]["email"] = ""
            page_data["user"]["enabled"] = True
            page_data["user"]["superuser"] = False
            page_data["user"]["created"] = "N/A"
            page_data["user"]["last_login"] = "N/A"
            page_data["user"]["last_ip"] = "N/A"
            page_data["user"]["last_update"] = "N/A"
            page_data["user"]["roles"] = set()
            page_data["user"]["hints"] = True
            page_data["superuser"] = superuser

            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                self.redirect(
                    "/panel/error?error=Unauthorized access: not a user editor"
                )
                return

            page_data["roles_all"] = self.controller.roles.get_all_roles()
            page_data["servers"] = []
            page_data["servers_all"] = self.controller.servers.get_all_defined_servers()
            page_data["role-servers"] = []
            page_data[
                "permissions_all"
            ] = self.controller.crafty_perms.list_defined_crafty_permissions()
            page_data["permissions_list"] = set()
            page_data[
                "quantity_server"
            ] = (
                self.controller.crafty_perms.list_all_crafty_permissions_quantity_limits()  # pylint: disable=line-too-long
            )
            page_data["languages"] = []
            page_data["languages"].append(
                self.controller.users.get_user_lang_by_id(exec_user["user_id"])
            )
            if superuser:
                page_data["super-disabled"] = ""
            else:
                page_data["super-disabled"] = "disabled"
            for file in sorted(
                os.listdir(os.path.join(self.helper.root_dir, "app", "translations"))
            ):
                if file.endswith(".json"):
                    if file not in self.helper.get_setting("disabled_language_files"):
                        if file != str(page_data["languages"][0] + ".json"):
                            page_data["languages"].append(file.split(".")[0])

            template = "panel/panel_edit_user.html"

        elif page == "add_schedule":
            server_id = self.get_argument("id", None)
            if server_id is None:
                return self.redirect("/panel/error?error=Invalid Schedule ID")
            server_obj = self.controller.servers.get_server_instance_by_id(server_id)
            page_data["backup_failed"] = server_obj.last_backup_status()
            server_obj = None
            page_data["schedules"] = HelpersManagement.get_schedules_by_server(
                server_id
            )
            page_data[
                "get_players"
            ] = lambda: self.controller.servers.stats.get_server_players(server_id)
            page_data["active_link"] = "schedules"
            page_data["permissions"] = {
                "Commands": EnumPermissionsServer.COMMANDS,
                "Terminal": EnumPermissionsServer.TERMINAL,
                "Logs": EnumPermissionsServer.LOGS,
                "Schedule": EnumPermissionsServer.SCHEDULE,
                "Backup": EnumPermissionsServer.BACKUP,
                "Files": EnumPermissionsServer.FILES,
                "Config": EnumPermissionsServer.CONFIG,
                "Players": EnumPermissionsServer.PLAYERS,
            }
            page_data[
                "user_permissions"
            ] = self.controller.server_perms.get_user_id_permissions_list(
                exec_user["user_id"], server_id
            )
            page_data["server_data"] = self.controller.servers.get_server_data_by_id(
                server_id
            )
            page_data["server_stats"] = self.controller.servers.get_server_stats_by_id(
                server_id
            )
            page_data["server_stats"][
                "server_type"
            ] = self.controller.servers.get_server_type_by_id(server_id)
            page_data["new_schedule"] = True
            page_data["schedule"] = {}
            page_data["schedule"]["children"] = []
            page_data["schedule"]["server_id"] = server_id
            page_data["schedule"]["schedule_id"] = ""
            page_data["schedule"]["action"] = ""
            page_data["schedule"]["enabled"] = True
            page_data["schedule"]["command"] = ""
            page_data["schedule"]["one_time"] = False
            page_data["schedule"]["cron_string"] = ""
            page_data["schedule"]["time"] = ""
            page_data["schedule"]["interval"] = ""
            # we don't need to check difficulty here.
            # We'll just default to basic for new schedules
            page_data["schedule"]["difficulty"] = "basic"
            page_data["schedule"]["interval_type"] = "days"

            if not EnumPermissionsServer.SCHEDULE in page_data["user_permissions"]:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access To Schedules")
                    return

            template = "panel/server_schedule_edit.html"

        elif page == "edit_schedule":
            server_id = self.check_server_id()
            if not server_id:
                return self.redirect("/panel/error?error=Invalid Schedule ID")
            server_obj = self.controller.servers.get_server_instance_by_id(server_id)
            page_data["backup_failed"] = server_obj.last_backup_status()
            server_obj = None

            page_data["schedules"] = HelpersManagement.get_schedules_by_server(
                server_id
            )
            sch_id = self.get_argument("sch_id", None)
            if sch_id is None:
                self.redirect("/panel/error?error=Invalid Schedule ID")
                return
            schedule = self.controller.management.get_scheduled_task_model(sch_id)
            page_data[
                "get_players"
            ] = lambda: self.controller.servers.stats.get_server_players(server_id)
            page_data["active_link"] = "schedules"
            page_data["permissions"] = {
                "Commands": EnumPermissionsServer.COMMANDS,
                "Terminal": EnumPermissionsServer.TERMINAL,
                "Logs": EnumPermissionsServer.LOGS,
                "Schedule": EnumPermissionsServer.SCHEDULE,
                "Backup": EnumPermissionsServer.BACKUP,
                "Files": EnumPermissionsServer.FILES,
                "Config": EnumPermissionsServer.CONFIG,
                "Players": EnumPermissionsServer.PLAYERS,
            }
            page_data[
                "user_permissions"
            ] = self.controller.server_perms.get_user_id_permissions_list(
                exec_user["user_id"], server_id
            )
            page_data["server_data"] = self.controller.servers.get_server_data_by_id(
                server_id
            )
            page_data["server_stats"] = self.controller.servers.get_server_stats_by_id(
                server_id
            )
            page_data["server_stats"][
                "server_type"
            ] = self.controller.servers.get_server_type_by_id(server_id)
            page_data["new_schedule"] = False
            page_data["schedule"] = {}
            page_data["schedule"]["server_id"] = server_id
            page_data["schedule"]["schedule_id"] = schedule.schedule_id
            page_data["schedule"]["action"] = schedule.action
            page_data["schedule"][
                "children"
            ] = self.controller.management.get_child_schedules(sch_id)
            # We check here to see if the command is any of the default ones.
            # We do not want a user changing to a custom command
            # and seeing our command there.
            if (
                schedule.action != "start"
                or schedule.action != "stop"
                or schedule.action != "restart"
                or schedule.action != "backup"
            ):
                page_data["schedule"]["command"] = schedule.command
            else:
                page_data["schedule"]["command"] = ""
            page_data["schedule"]["enabled"] = schedule.enabled
            page_data["schedule"]["one_time"] = schedule.one_time
            page_data["schedule"]["cron_string"] = schedule.cron_string
            page_data["schedule"]["time"] = schedule.start_time
            page_data["schedule"]["interval"] = schedule.interval
            page_data["schedule"]["interval_type"] = schedule.interval_type
            if schedule.interval_type == "reaction":
                difficulty = "reaction"
            elif schedule.cron_string == "":
                difficulty = "basic"
            else:
                difficulty = "advanced"
            page_data["schedule"]["difficulty"] = difficulty

            if not EnumPermissionsServer.SCHEDULE in page_data["user_permissions"]:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access To Schedules")
                    return

            template = "panel/server_schedule_edit.html"

        elif page == "edit_user":
            user_id = self.get_argument("id", None)
            role_servers = self.controller.servers.get_authorized_servers(user_id)
            page_role_servers = []
            for server in role_servers:
                page_role_servers.append(server.server_id)
            page_data["new_user"] = False
            page_data["user"] = self.controller.users.get_user_by_id(user_id)
            page_data["servers"] = set()
            page_data["role-servers"] = page_role_servers
            page_data["roles_all"] = self.controller.roles.get_all_roles()
            page_data["servers_all"] = self.controller.servers.get_all_defined_servers()
            page_data["superuser"] = superuser
            page_data[
                "permissions_all"
            ] = self.controller.crafty_perms.list_defined_crafty_permissions()
            page_data[
                "permissions_list"
            ] = self.controller.crafty_perms.get_crafty_permissions_list(user_id)
            page_data[
                "quantity_server"
            ] = self.controller.crafty_perms.list_crafty_permissions_quantity_limits(
                user_id
            )
            page_data["languages"] = []
            page_data["languages"].append(
                self.controller.users.get_user_lang_by_id(user_id)
            )
            # checks if super user. If not we disable the button.
            if superuser and str(exec_user["user_id"]) != str(user_id):
                page_data["super-disabled"] = ""
            else:
                page_data["super-disabled"] = "disabled"

            for file in sorted(
                os.listdir(os.path.join(self.helper.root_dir, "app", "translations"))
            ):
                if file.endswith(".json"):
                    if file not in self.helper.get_setting("disabled_language_files"):
                        if file != str(page_data["languages"][0] + ".json"):
                            page_data["languages"].append(file.split(".")[0])

            if user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                if str(user_id) != str(exec_user["user_id"]):
                    self.redirect(
                        "/panel/error?error=Unauthorized access: not a user editor"
                    )
                    return

                page_data["servers"] = []
                page_data["role-servers"] = []
                page_data["roles_all"] = []
                page_data["servers_all"] = []

            if exec_user["user_id"] != page_data["user"]["user_id"]:
                page_data["user"]["api_token"] = "********"

            if exec_user["email"] == "default@example.com":
                page_data["user"]["email"] = ""
            template = "panel/panel_edit_user.html"

        elif page == "edit_user_apikeys":
            user_id = self.get_argument("id", None)
            page_data["user"] = self.controller.users.get_user_by_id(user_id)
            page_data["api_keys"] = self.controller.users.get_user_api_keys(user_id)
            # self.controller.crafty_perms.list_defined_crafty_permissions()
            page_data[
                "server_permissions_all"
            ] = self.controller.server_perms.list_defined_permissions()
            page_data[
                "crafty_permissions_all"
            ] = self.controller.crafty_perms.list_defined_crafty_permissions()

            if user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            if int(user_id) != exec_user["user_id"] and not exec_user["superuser"]:
                self.redirect(
                    "/panel/error?error=You are not authorized to view this page."
                )
                return

            template = "panel/panel_edit_user_apikeys.html"

        elif page == "remove_user":
            user_id = bleach.clean(self.get_argument("id", None))

            if (
                not superuser
                and EnumPermissionsCrafty.USER_CONFIG
                not in exec_user_crafty_permissions
            ):
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return

            if str(exec_user["user_id"]) == str(user_id):
                self.redirect(
                    "/panel/error?error=Unauthorized access: you cannot delete yourself"
                )
                return
            if user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            # does this user id exist?
            target_user = self.controller.users.get_user_by_id(user_id)
            if not target_user:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            if target_user["superuser"]:
                self.redirect("/panel/error?error=Cannot remove a superuser")
                return

            self.controller.users.remove_user(user_id)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Removed user {target_user['username']} (UID:{user_id})",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.redirect("/panel/panel_config")

        elif page == "add_role":
            user_roles = self.get_user_roles()
            page_data["new_role"] = True
            page_data["role"] = {}
            page_data["role"]["role_name"] = ""
            page_data["role"]["role_id"] = -1
            page_data["role"]["created"] = "N/A"
            page_data["role"]["last_update"] = "N/A"
            page_data["role"]["servers"] = set()
            page_data["user-roles"] = user_roles
            page_data["users"] = self.controller.users.get_all_users()

            if EnumPermissionsCrafty.ROLES_CONFIG not in exec_user_crafty_permissions:
                self.redirect(
                    "/panel/error?error=Unauthorized access: not a role editor"
                )
                return
            if exec_user["superuser"]:
                defined_servers = self.controller.servers.list_defined_servers()
            else:
                defined_servers = self.controller.servers.get_authorized_servers(
                    exec_user["user_id"]
                )
            page_servers = []
            for server in defined_servers:
                if server not in page_servers:
                    page_servers.append(
                        DatabaseShortcuts.get_data_obj(server.server_object)
                    )
            page_data["servers_all"] = page_servers
            page_data[
                "permissions_all"
            ] = self.controller.server_perms.list_defined_permissions()
            page_data["permissions_dict"] = {}
            template = "panel/panel_edit_role.html"

        elif page == "edit_role":
            user_roles = self.get_user_roles()
            page_data["new_role"] = False
            role_id = self.get_argument("id", None)
            page_data["role"] = self.controller.roles.get_role_with_servers(role_id)
            if exec_user["superuser"]:
                defined_servers = self.controller.servers.list_defined_servers()
            else:
                defined_servers = self.controller.servers.get_authorized_servers(
                    exec_user["user_id"]
                )
            page_servers = []
            for server in defined_servers:
                if server not in page_servers:
                    page_servers.append(
                        DatabaseShortcuts.get_data_obj(server.server_object)
                    )
            page_data["servers_all"] = page_servers
            page_data[
                "permissions_all"
            ] = self.controller.server_perms.list_defined_permissions()
            page_data[
                "permissions_dict"
            ] = self.controller.server_perms.get_role_permissions_dict(role_id)
            page_data["user-roles"] = user_roles
            page_data["users"] = self.controller.users.get_all_users()

            if EnumPermissionsCrafty.ROLES_CONFIG not in exec_user_crafty_permissions:
                self.redirect(
                    "/panel/error?error=Unauthorized access: not a role editor"
                )
                return
            if role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return

            template = "panel/panel_edit_role.html"

        elif page == "remove_role":
            role_id = bleach.clean(self.get_argument("id", None))

            if not superuser:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return
            if role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return
            # does this user id exist?
            target_role = self.controller.roles.get_role(role_id)
            if not target_role:
                self.redirect("/panel/error?error=Invalid Role ID")
                return

            self.controller.roles.remove_role(role_id)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Removed role {target_role['role_name']} (RID:{role_id})",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.redirect("/panel/panel_config")

        elif page == "activity_logs":
            page_data["audit_logs"] = self.controller.management.get_actity_log()

            template = "panel/activity_logs.html"

        elif page == "download_file":
            file = Helpers.get_os_understandable_path(self.get_argument("path", ""))
            name = self.get_argument("name", "")

            server_id = self.check_server_id()
            if server_id is None:
                return

            server_info = self.controller.servers.get_server_data_by_id(server_id)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(server_info["path"]), file
            ) or not os.path.isfile(file):
                self.redirect("/panel/error?error=Invalid path detected")
                return

            self.download_file(name, file)
            self.redirect(f"/panel/server_detail?id={server_id}&subpage=files")

        elif page == "wiki":
            template = "panel/wiki.html"

        elif page == "download_support_package":
            temp_zip_storage = exec_user["support_logs"]

            self.set_header("Content-Type", "application/octet-stream")
            self.set_header(
                "Content-Disposition", "attachment; filename=" + "support_logs.zip"
            )
            chunk_size = 1024 * 1024 * 4  # 4 MiB
            if temp_zip_storage != "":
                with open(temp_zip_storage, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        try:
                            self.write(chunk)  # write the chunk to response
                            self.flush()  # send the chunk to client
                        except iostream.StreamClosedError:
                            # this means the client has closed the connection
                            # so break the loop
                            break
                        finally:
                            # deleting the chunk is very important because
                            # if many clients are downloading files at the
                            # same time, the chunks in memory will keep
                            # increasing and will eat up the RAM
                            del chunk
                self.redirect("/panel/dashboard")
            else:
                self.redirect("/panel/error?error=No path found for support logs")
                return

        elif page == "support_logs":
            logger.info(
                f"Support logs requested. "
                f"Packinging logs for user with ID: {exec_user['user_id']}"
            )
            logs_thread = threading.Thread(
                target=self.controller.package_support_logs,
                daemon=True,
                args=(exec_user,),
                name=f"{exec_user['user_id']}_logs_thread",
            )
            logs_thread.start()
            self.redirect("/panel/dashboard")
            return

        self.render(
            template,
            data=page_data,
            time=time,
            utc_offset=(time.timezone * -1 / 60 / 60),
            translate=self.translator.translate,
        )

    @tornado.web.authenticated
    def post(self, page):
        api_key, _token_data, exec_user = self.current_user
        superuser = exec_user["superuser"]
        if api_key is not None:
            superuser = superuser and api_key.superuser

        server_id = self.get_argument("id", None)
        permissions = {
            "Commands": EnumPermissionsServer.COMMANDS,
            "Terminal": EnumPermissionsServer.TERMINAL,
            "Logs": EnumPermissionsServer.LOGS,
            "Schedule": EnumPermissionsServer.SCHEDULE,
            "Backup": EnumPermissionsServer.BACKUP,
            "Files": EnumPermissionsServer.FILES,
            "Config": EnumPermissionsServer.CONFIG,
            "Players": EnumPermissionsServer.PLAYERS,
        }
        if superuser:
            # defined_servers = self.controller.servers.list_defined_servers()
            exec_user_role = {"Super User"}
            exec_user_crafty_permissions = (
                self.controller.crafty_perms.list_defined_crafty_permissions()
            )
        else:
            exec_user_crafty_permissions = (
                self.controller.crafty_perms.get_crafty_permissions_list(
                    exec_user["user_id"]
                )
            )
            # defined_servers =
            # self.controller.servers.get_authorized_servers(exec_user["user_id"])
            exec_user_role = set()
            for r in exec_user["roles"]:
                role = self.controller.roles.get_role(r)
                exec_user_role.add(role["role_name"])

        if page == "server_detail":
            if not permissions[
                "Config"
            ] in self.controller.server_perms.get_user_id_permissions_list(
                exec_user["user_id"], server_id
            ):
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Config")
                    return
            server_name = self.get_argument("server_name", None)
            server_obj = self.controller.servers.get_server_obj(server_id)
            if superuser:
                server_path = self.get_argument("server_path", None)
                if Helpers.is_os_windows():
                    server_path.replace(" ", "^ ")
                    server_path = Helpers.wtol_path(server_path)
                log_path = self.get_argument("log_path", None)
                if Helpers.is_os_windows():
                    log_path.replace(" ", "^ ")
                    log_path = Helpers.wtol_path(log_path)
                if not self.helper.validate_traversal(server_obj.path, log_path):
                    log_path = ""
                executable = self.get_argument("executable", None)
                execution_command = self.get_argument("execution_command", None)
                server_ip = self.get_argument("server_ip", None)
                server_port = self.get_argument("server_port", None)
                executable_update_url = self.get_argument("executable_update_url", None)
            else:
                execution_command = server_obj.execution_command
                executable = server_obj.executable
            stop_command = self.get_argument("stop_command", None)
            auto_start_delay = self.get_argument("auto_start_delay", "10")
            auto_start = int(float(self.get_argument("auto_start", "0")))
            crash_detection = int(float(self.get_argument("crash_detection", "0")))
            logs_delete_after = int(float(self.get_argument("logs_delete_after", "0")))
            java_selection = self.get_argument("java_selection", None)
            # subpage = self.get_argument('subpage', None)

            server_id = self.check_server_id()
            if server_id is None:
                return
            if java_selection:
                try:
                    execution_list = shlex.split(execution_command)
                except ValueError:
                    self.redirect(
                        "/panel/error?error=Invalid execution command. Java path"
                        " must be surrounded by quotes."
                        " (Are you missing a closing quote?)"
                    )
                if (
                    not any(
                        java_selection in path for path in Helpers.find_java_installs()
                    )
                    and java_selection != "java"
                ):
                    self.redirect(
                        "/panel/error?error=Attack attempted."
                        + " A copy of this report is being sent to server owner."
                    )
                    self.controller.management.add_to_audit_log_raw(
                        exec_user["username"],
                        exec_user["user_id"],
                        server_id,
                        f"Attempted to send bad java path for {server_id}."
                        + " Possible attack. Act accordingly.",
                        self.get_remote_ip(),
                    )
                    return
                if java_selection != "java":
                    if self.helper.is_os_windows():
                        execution_list[0] = '"' + java_selection + '/bin/java"'
                    else:
                        execution_list[0] = '"' + java_selection + '"'
                else:
                    execution_list[0] = "java"
                execution_command = ""
                for item in execution_list:
                    execution_command += item + " "

            server_obj: Servers = self.controller.servers.get_server_obj(server_id)
            stale_executable = server_obj.executable
            # Compares old jar name to page data being passed.
            # If they are different we replace the executable name in the
            if str(stale_executable) != str(executable):
                execution_command = execution_command.replace(
                    str(stale_executable), str(executable)
                )

            server_obj.server_name = server_name
            if superuser:
                if Helpers.validate_traversal(
                    self.helper.get_servers_root_dir(), server_path
                ):
                    server_obj.path = server_path
                    server_obj.log_path = log_path
                if Helpers.validate_traversal(
                    self.helper.get_servers_root_dir(), executable
                ):
                    server_obj.executable = executable
                server_obj.execution_command = execution_command
                server_obj.server_ip = server_ip
                server_obj.server_port = server_port
                server_obj.executable_update_url = executable_update_url
            else:
                server_obj.path = server_obj.path
                server_obj.log_path = server_obj.log_path
                server_obj.executable = server_obj.executable
                server_obj.execution_command = execution_command
                server_obj.server_ip = server_obj.server_ip
                server_obj.server_port = server_obj.server_port
                server_obj.executable_update_url = server_obj.executable_update_url
            server_obj.stop_command = stop_command
            server_obj.auto_start_delay = auto_start_delay
            server_obj.auto_start = auto_start
            server_obj.crash_detection = crash_detection
            server_obj.logs_delete_after = logs_delete_after
            self.controller.servers.update_server(server_obj)
            self.controller.servers.crash_detection(server_obj)

            self.controller.servers.refresh_server_settings(server_id)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Edited server {server_id} named {server_name}",
                server_id,
                self.get_remote_ip(),
            )

            self.redirect(f"/panel/server_detail?id={server_id}&subpage=config")

        if page == "server_backup":
            logger.debug(self.request.arguments)

            server_id = self.check_server_id()
            if not server_id:
                return

            if (
                not permissions["Backup"]
                in self.controller.server_perms.get_user_id_permissions_list(
                    exec_user["user_id"], server_id
                )
                and not superuser
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: User not authorized"
                )
                return

            server_obj = self.controller.servers.get_server_obj(server_id)
            compress = self.get_argument("compress", False)
            shutdown = self.get_argument("shutdown", False)
            check_changed = self.get_argument("changed")
            if str(check_changed) == str(1):
                checked = self.get_body_arguments("root_path")
            else:
                checked = self.controller.management.get_excluded_backup_dirs(server_id)
            if superuser:
                backup_path = bleach.clean(self.get_argument("backup_path", None))
                if Helpers.is_os_windows():
                    backup_path.replace(" ", "^ ")
                    backup_path = Helpers.wtol_path(backup_path)
            else:
                backup_path = server_obj.backup_path
            max_backups = bleach.clean(self.get_argument("max_backups", None))

            server_obj = self.controller.servers.get_server_obj(server_id)

            server_obj.backup_path = backup_path
            self.controller.servers.update_server(server_obj)
            self.controller.management.set_backup_config(
                server_id,
                max_backups=max_backups,
                excluded_dirs=checked,
                compress=bool(compress),
                shutdown=bool(shutdown),
            )

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Edited server {server_id}: updated backups",
                server_id,
                self.get_remote_ip(),
            )
            self.tasks_manager.reload_schedule_from_db()
            self.redirect(f"/panel/server_detail?id={server_id}&subpage=backup")

        if page == "new_schedule":
            server_id = self.check_server_id()
            if not server_id:
                return

            if (
                not permissions["Schedule"]
                in self.controller.server_perms.get_user_id_permissions_list(
                    exec_user["user_id"], server_id
                )
                and not superuser
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: User not authorized"
                )
                return

            difficulty = bleach.clean(self.get_argument("difficulty", None))
            server_obj = self.controller.servers.get_server_obj(server_id)
            enabled = bleach.clean(self.get_argument("enabled", "0"))
            if difficulty == "basic":
                action = bleach.clean(self.get_argument("action", None))
                interval = bleach.clean(self.get_argument("interval", None))
                interval_type = bleach.clean(self.get_argument("interval_type", None))
                # only check for time if it's number of days
                if interval_type == "days":
                    sch_time = bleach.clean(self.get_argument("time", None))
                if action == "command":
                    command = bleach.clean(self.get_argument("command", None))
                elif action == "start":
                    command = "start_server"
                elif action == "stop":
                    command = "stop_server"
                elif action == "restart":
                    command = "restart_server"
                elif action == "backup":
                    command = "backup_server"

            elif difficulty == "reaction":
                interval_type = "reaction"
                action = bleach.clean(self.get_argument("action", None))
                delay = bleach.clean(self.get_argument("delay", None))
                parent = bleach.clean(self.get_argument("parent", None))
                if action == "command":
                    command = bleach.clean(self.get_argument("command", None))
                elif action == "start":
                    command = "start_server"
                elif action == "stop":
                    command = "stop_server"
                elif action == "restart":
                    command = "restart_server"
                elif action == "backup":
                    command = "backup_server"

            else:
                interval_type = ""
                cron_string = bleach.clean(self.get_argument("cron", ""))
                if not croniter.is_valid(cron_string):
                    self.redirect(
                        "/panel/error?error=INVALID FORMAT: Invalid Cron Format."
                    )
                    return
                action = bleach.clean(self.get_argument("action", None))
                if action == "command":
                    command = bleach.clean(self.get_argument("command", None))
                elif action == "start":
                    command = "start_server"
                elif action == "stop":
                    command = "stop_server"
                elif action == "restart":
                    command = "restart_server"
                elif action == "backup":
                    command = "backup_server"
            if bleach.clean(self.get_argument("enabled", "0")) == "1":
                enabled = True
            else:
                enabled = False
            if bleach.clean(self.get_argument("one_time", "0")) == "1":
                one_time = True
            else:
                one_time = False

            if interval_type == "days":
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": interval_type,
                    "interval": interval,
                    "command": command,
                    "start_time": sch_time,
                    "enabled": enabled,
                    "one_time": one_time,
                    "cron_string": "",
                    "parent": None,
                    "delay": 0,
                }
            elif difficulty == "reaction":
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": interval_type,
                    "interval": "",
                    # We'll base every interval off of a midnight start time.
                    "start_time": "",
                    "command": command,
                    "cron_string": "",
                    "enabled": enabled,
                    "one_time": one_time,
                    "parent": parent,
                    "delay": delay,
                }
            elif difficulty == "advanced":
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": "",
                    "interval": "",
                    # We'll base every interval off of a midnight start time.
                    "start_time": "",
                    "command": command,
                    "cron_string": cron_string,
                    "enabled": enabled,
                    "one_time": one_time,
                    "parent": None,
                    "delay": 0,
                }
            else:
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": interval_type,
                    "interval": interval,
                    "command": command,
                    "enabled": enabled,
                    # We'll base every interval off of a midnight start time.
                    "start_time": "00:00",
                    "one_time": one_time,
                    "cron_string": "",
                    "parent": None,
                    "delay": 0,
                }

            self.tasks_manager.schedule_job(job_data)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Edited server {server_id}: added scheduled job",
                server_id,
                self.get_remote_ip(),
            )
            self.tasks_manager.reload_schedule_from_db()
            self.redirect(f"/panel/server_detail?id={server_id}&subpage=schedules")

        if page == "edit_schedule":
            server_id = self.check_server_id()
            if not server_id:
                return

            if (
                not permissions["Schedule"]
                in self.controller.server_perms.get_user_id_permissions_list(
                    exec_user["user_id"], server_id
                )
                and not superuser
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: User not authorized"
                )
                return

            sch_id = self.get_argument("sch_id", None)
            if sch_id is None:
                self.redirect("/panel/error?error=Invalid Schedule ID")

            difficulty = bleach.clean(self.get_argument("difficulty", None))
            server_obj = self.controller.servers.get_server_obj(server_id)
            enabled = bleach.clean(self.get_argument("enabled", "0"))
            if difficulty == "basic":
                action = bleach.clean(self.get_argument("action", None))
                interval = bleach.clean(self.get_argument("interval", None))
                interval_type = bleach.clean(self.get_argument("interval_type", None))
                # only check for time if it's number of days
                if interval_type == "days":
                    sch_time = bleach.clean(self.get_argument("time", None))
                if action == "command":
                    command = bleach.clean(self.get_argument("command", None))
                elif action == "start":
                    command = "start_server"
                elif action == "stop":
                    command = "stop_server"
                elif action == "restart":
                    command = "restart_server"
                elif action == "backup":
                    command = "backup_server"
            elif difficulty == "reaction":
                interval_type = "reaction"
                action = bleach.clean(self.get_argument("action", None))
                delay = bleach.clean(self.get_argument("delay", None))
                parent = bleach.clean(self.get_argument("parent", None))
                if action == "command":
                    command = bleach.clean(self.get_argument("command", None))
                elif action == "start":
                    command = "start_server"
                elif action == "stop":
                    command = "stop_server"
                elif action == "restart":
                    command = "restart_server"
                elif action == "backup":
                    command = "backup_server"
                parent = bleach.clean(self.get_argument("parent", None))
            else:
                interval_type = ""
                cron_string = bleach.clean(self.get_argument("cron", ""))
                if not croniter.is_valid(cron_string):
                    self.redirect(
                        "/panel/error?error=INVALID FORMAT: Invalid Cron Format."
                    )
                    return
                action = bleach.clean(self.get_argument("action", None))
                if action == "command":
                    command = bleach.clean(self.get_argument("command", None))
                elif action == "start":
                    command = "start_server"
                elif action == "stop":
                    command = "stop_server"
                elif action == "restart":
                    command = "restart_server"
                elif action == "backup":
                    command = "backup_server"
            if bleach.clean(self.get_argument("enabled", "0")) == "1":
                enabled = True
            else:
                enabled = False
            if bleach.clean(self.get_argument("one_time", "0")) == "1":
                one_time = True
            else:
                one_time = False

            if interval_type == "days":
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": interval_type,
                    "interval": interval,
                    "command": command,
                    "start_time": sch_time,
                    "enabled": enabled,
                    "one_time": one_time,
                    "cron_string": "",
                    "parent": None,
                    "delay": 0,
                }
            elif difficulty == "advanced":
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": "",
                    "interval": "",
                    # We'll base every interval off of a midnight start time.
                    "start_time": "",
                    "command": command,
                    "cron_string": cron_string,
                    "delay": "",
                    "parent": "",
                    "enabled": enabled,
                    "one_time": one_time,
                }
            elif difficulty == "reaction":
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": interval_type,
                    "interval": "",
                    # We'll base every interval off of a midnight start time.
                    "start_time": "",
                    "command": command,
                    "cron_string": "",
                    "enabled": enabled,
                    "one_time": one_time,
                    "parent": parent,
                    "delay": delay,
                }
            else:
                job_data = {
                    "server_id": server_id,
                    "action": action,
                    "interval_type": interval_type,
                    "interval": interval,
                    "command": command,
                    "enabled": enabled,
                    # We'll base every interval off of a midnight start time.
                    "start_time": "00:00",
                    "delay": "",
                    "parent": "",
                    "one_time": one_time,
                    "cron_string": "",
                }
            self.tasks_manager.update_job(sch_id, job_data)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Edited server {server_id}: updated schedule",
                server_id,
                self.get_remote_ip(),
            )
            self.tasks_manager.reload_schedule_from_db()
            self.redirect(f"/panel/server_detail?id={server_id}&subpage=schedules")

        elif page == "edit_user":
            if bleach.clean(self.get_argument("username", None)).lower() == "system":
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "system user is not editable"
                )
            user_id = bleach.clean(self.get_argument("id", None))
            username = bleach.clean(self.get_argument("username", None).lower())
            if (
                username != self.controller.users.get_user_by_id(user_id)["username"]
                and username in self.controller.users.get_all_usernames()
            ):
                self.redirect(
                    "/panel/error?error=Duplicate User: Useranme already exists."
                )
            password0 = bleach.clean(self.get_argument("password0", None))
            password1 = bleach.clean(self.get_argument("password1", None))
            email = bleach.clean(self.get_argument("email", "default@example.com"))
            enabled = int(float(self.get_argument("enabled", "0")))
            try:
                hints = int(bleach.clean(self.get_argument("hints")))
                hints = True
            except:
                hints = False
            lang = bleach.clean(
                self.get_argument("language"), self.helper.get_setting("language")
            )

            if superuser:
                # Checks if user is trying to change super user status of self.
                # We don't want that. Automatically make them stay super user
                # since we know they are.
                if str(exec_user["user_id"]) != str(user_id):
                    superuser = bleach.clean(self.get_argument("superuser", "0"))
                else:
                    superuser = "1"
            else:
                superuser = "0"
            if superuser == "1":
                superuser = True
            else:
                superuser = False
            if not exec_user["superuser"]:
                if username is None or username == "":
                    self.redirect("/panel/error?error=Invalid username")
                    return
                if user_id is None:
                    self.redirect("/panel/error?error=Invalid User ID")
                    return
                if (
                    EnumPermissionsCrafty.USER_CONFIG
                    not in exec_user_crafty_permissions
                ):
                    if str(user_id) != str(exec_user["user_id"]):
                        self.redirect(
                            "/panel/error?error=Unauthorized access: not a user editor"
                        )
                        return

                    user_data = {
                        "username": username,
                        "password": password0,
                        "email": email,
                        "lang": lang,
                        "hints": hints,
                    }
                    self.controller.users.update_user(user_id, user_data=user_data)

                    self.controller.management.add_to_audit_log(
                        exec_user["user_id"],
                        f"Edited user {username} (UID:{user_id}) password",
                        server_id=0,
                        source_ip=self.get_remote_ip(),
                    )
                    self.redirect("/panel/panel_config")
                    return
                # does this user id exist?
                if not self.controller.users.user_id_exists(user_id):
                    self.redirect("/panel/error?error=Invalid User ID")
                    return
            else:
                if password0 != password1:
                    self.redirect("/panel/error?error=Passwords must match")
                    return

                roles = self.get_user_role_memberships()
                permissions_mask, server_quantity = self.get_perms_quantity()

                # if email is None or "":
                #     email = "default@example.com"

                user_data = {
                    "username": username,
                    "password": password0,
                    "email": email,
                    "enabled": enabled,
                    "roles": roles,
                    "lang": lang,
                    "superuser": superuser,
                    "hints": hints,
                }
                user_crafty_data = {
                    "permissions_mask": permissions_mask,
                    "server_quantity": server_quantity,
                }
                self.controller.users.update_user(
                    user_id, user_data=user_data, user_crafty_data=user_crafty_data
                )

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Edited user {username} (UID:{user_id}) with roles {roles} "
                f"and permissions {permissions_mask}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.redirect("/panel/panel_config")

        elif page == "edit_user_apikeys":
            user_id = self.get_argument("id", None)
            name = self.get_argument("name", None)
            superuser = self.get_argument("superuser", None) == "1"

            if name is None or name == "":
                self.redirect("/panel/error?error=Invalid API key name")
                return
            if user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            # does this user id exist?
            if not self.controller.users.user_id_exists(user_id):
                self.redirect("/panel/error?error=Invalid User ID")
                return

            if str(user_id) != str(exec_user["user_id"]) and not exec_user["superuser"]:
                self.redirect(
                    "/panel/error?error=You do not have access to change"
                    + "this user's api key."
                )
                return

            crafty_permissions_mask = self.get_perms()
            server_permissions_mask = self.get_perms_server()

            self.controller.users.add_user_api_key(
                name,
                user_id,
                superuser,
                server_permissions_mask,
                crafty_permissions_mask,
            )

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Added API key {name} with crafty permissions "
                f"{crafty_permissions_mask}"
                f" and {server_permissions_mask} for user with UID: {user_id}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.redirect(f"/panel/edit_user_apikeys?id={user_id}")

        elif page == "get_token":
            key_id = self.get_argument("id", None)

            if key_id is None:
                self.redirect("/panel/error?error=Invalid Key ID")
                return
            key = self.controller.users.get_user_api_key(key_id)
            # does this user id exist?
            if key is None:
                self.redirect("/panel/error?error=Invalid Key ID")
                return

            if (
                str(key.user_id) != str(exec_user["user_id"])
                and not exec_user["superuser"]
            ):
                self.redirect(
                    "/panel/error?error=You are not authorized to access this key."
                )
                return

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Generated a new API token for the key {key.name} "
                f"from user with UID: {key.user_id}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )

            self.write(
                self.controller.authentication.generate(
                    key.user_id_id, {"token_id": key.token_id}
                )
            )
            self.finish()

        elif page == "add_user":
            username = bleach.clean(self.get_argument("username", None).lower())
            if username.lower() == "system":
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "username system is reserved for the Crafty system."
                    " Please choose a different username."
                )
                return
            password0 = bleach.clean(self.get_argument("password0", None))
            password1 = bleach.clean(self.get_argument("password1", None))
            email = bleach.clean(self.get_argument("email", "default@example.com"))
            enabled = int(float(self.get_argument("enabled", "0")))
            hints = True
            lang = bleach.clean(
                self.get_argument("lang", self.helper.get_setting("language"))
            )
            # We don't want a non-super user to be able to create a super user.
            if superuser:
                new_superuser = bleach.clean(self.get_argument("superuser", "0"))
            else:
                new_superuser = "0"
            if superuser == "1":
                new_superuser = True
            else:
                new_superuser = False

            if EnumPermissionsCrafty.USER_CONFIG not in exec_user_crafty_permissions:
                self.redirect(
                    "/panel/error?error=Unauthorized access: not a user editor"
                )
                return

            if (
                not self.controller.crafty_perms.can_add_user(exec_user["user_id"])
                and not exec_user["superuser"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: quantity limit reached"
                )
                return
            if username is None or username == "":
                self.redirect("/panel/error?error=Invalid username")
                return
            # does this user id exist?
            if self.controller.users.get_id_by_name(username) is not None:
                self.redirect("/panel/error?error=User exists")
                return

            if password0 != password1:
                self.redirect("/panel/error?error=Passwords must match")
                return

            roles = self.get_user_role_memberships()
            permissions_mask, server_quantity = self.get_perms_quantity()

            user_id = self.controller.users.add_user(
                username,
                password=password0,
                email=email,
                enabled=enabled,
                superuser=new_superuser,
            )
            user_data = {"roles": roles, "lang": lang, "hints": True}
            user_crafty_data = {
                "permissions_mask": permissions_mask,
                "server_quantity": server_quantity,
            }
            self.controller.users.update_user(
                user_id, user_data=user_data, user_crafty_data=user_crafty_data
            )

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Added user {username} (UID:{user_id})",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Edited user {username} (UID:{user_id}) with roles {roles}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.controller.crafty_perms.add_user_creation(exec_user["user_id"])
            self.redirect("/panel/panel_config")

        elif page == "edit_role":
            role_id = bleach.clean(self.get_argument("id", None))
            role_name = bleach.clean(self.get_argument("role_name", None))

            if EnumPermissionsCrafty.ROLES_CONFIG not in exec_user_crafty_permissions:
                self.redirect(
                    "/panel/error?error=Unauthorized access: not a role editor"
                )
                return
            if role_name is None or role_name == "":
                self.redirect("/panel/error?error=Invalid username")
                return
            if role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return
            # does this user id exist?
            if not self.controller.roles.role_id_exists(role_id):
                self.redirect("/panel/error?error=Invalid Role ID")
                return

            servers = self.get_role_servers()

            self.controller.roles.update_role_advanced(role_id, role_name, servers)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"edited role {role_name} (RID:{role_id}) with servers {servers}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.redirect("/panel/panel_config")

        elif page == "add_role":
            role_name = bleach.clean(self.get_argument("role_name", None))

            if EnumPermissionsCrafty.ROLES_CONFIG not in exec_user_crafty_permissions:
                self.redirect(
                    "/panel/error?error=Unauthorized access: not a role editor"
                )
                return
            if (
                not self.controller.crafty_perms.can_add_role(exec_user["user_id"])
                and not exec_user["superuser"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: quantity limit reached"
                )
                return
            if role_name is None or role_name == "":
                self.redirect("/panel/error?error=Invalid role name")
                return
            # does this user id exist?
            if self.controller.roles.get_roleid_by_name(role_name) is not None:
                self.redirect("/panel/error?error=Role exists")
                return

            servers = self.get_role_servers()

            role_id = self.controller.roles.add_role_advanced(role_name, servers)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"created role {role_name} (RID:{role_id})",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.controller.crafty_perms.add_role_creation(exec_user["user_id"])
            self.redirect("/panel/panel_config")

        else:
            self.set_status(404)
            page_data = {
                "lang": self.helper.get_setting("language"),
                "lang_page": Helpers.get_lang_page(self.helper.get_setting("language")),
            }
            self.render(
                "public/404.html", translate=self.translator.translate, data=page_data
            )

    @tornado.web.authenticated
    def delete(self, page):
        api_key, _token_data, exec_user = self.current_user
        superuser = exec_user["superuser"]
        if api_key is not None:
            superuser = superuser and api_key.superuser

        page_data = {
            # todo: make this actually pull and compare version data
            "update_available": False,
            "version_data": self.helper.get_version_string(),
            "user_data": exec_user,
            "hosts_data": self.controller.management.get_latest_hosts_stats(),
            "show_contribute": self.helper.get_setting("show_contribute_link", True),
            "lang": self.controller.users.get_user_lang_by_id(exec_user["user_id"]),
            "lang_page": Helpers.get_lang_page(
                self.controller.users.get_user_lang_by_id(exec_user["user_id"])
            ),
        }

        if page == "remove_apikey":
            key_id = bleach.clean(self.get_argument("id", None))

            if not superuser:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return
            if key_id is None or self.controller.users.get_user_api_key(key_id) is None:
                self.redirect("/panel/error?error=Invalid Key ID")
                return
            # does this user id exist?
            target_key = self.controller.users.get_user_api_key(key_id)
            if not target_key:
                self.redirect("/panel/error?error=Invalid Key ID")
                return

            key_obj = self.controller.users.get_user_api_key(key_id)

            if key_obj.user_id != exec_user["user_id"] and not exec_user["superuser"]:
                self.redirect(
                    "/panel/error?error=You do not have access to change"
                    + "this user's api key."
                )
                return

            self.controller.users.delete_user_api_key(key_id)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Removed API key {target_key} "
                f"(ID: {key_id}) from user {exec_user['user_id']}",
                server_id=0,
                source_ip=self.get_remote_ip(),
            )
            self.finish()
            self.redirect(f"/panel/edit_user_apikeys?id={key_obj.user_id}")
        else:
            self.set_status(404)
            self.render(
                "public/404.html",
                data=page_data,
                translate=self.translator.translate,
            )

from datetime import datetime
import logging
import re

from app.classes.controllers.crafty_perms_controller import EnumPermissionsCrafty
from app.classes.controllers.server_perms_controller import EnumPermissionsServer
from app.classes.web.base_handler import BaseHandler
from app.classes.models.management import DatabaseShortcuts

logger = logging.getLogger(__name__)
bearer_pattern = re.compile(r"^Bearer", flags=re.IGNORECASE)


class ApiHandler(BaseHandler):
    def return_response(self, status: int, data: dict):
        # Define a standardized response
        self.set_status(status)
        self.write(data)

    def check_xsrf_cookie(self):
        # Disable CSRF protection on API routes
        pass

    def access_denied(self, user, reason=""):
        if reason:
            reason = " because " + reason
        logger.info(
            "User %s from IP %s was denied access to the API route "
            + self.request.path
            + reason,
            user,
            self.get_remote_ip(),
        )
        self.finish(
            self.return_response(
                403,
                {
                    "error": "ACCESS_DENIED",
                    "info": "You were denied access to the requested resource",
                },
            )
        )

    def authenticate_user(self) -> bool:
        self.permissions = {
            "Commands": EnumPermissionsServer.COMMANDS,
            "Terminal": EnumPermissionsServer.TERMINAL,
            "Logs": EnumPermissionsServer.LOGS,
            "Schedule": EnumPermissionsServer.SCHEDULE,
            "Backup": EnumPermissionsServer.BACKUP,
            "Files": EnumPermissionsServer.FILES,
            "Config": EnumPermissionsServer.CONFIG,
            "Players": EnumPermissionsServer.PLAYERS,
            "Server_Creation": EnumPermissionsCrafty.SERVER_CREATION,
            "User_Config": EnumPermissionsCrafty.USER_CONFIG,
            "Roles_Config": EnumPermissionsCrafty.ROLES_CONFIG,
        }
        try:
            logger.debug("Searching for specified token")

            api_token = self.get_argument("token", "")
            self.api_token = api_token
            if api_token is None and self.request.headers.get("Authorization"):
                api_token = bearer_pattern.sub(
                    "", self.request.headers.get("Authorization")
                )
            elif api_token is None:
                api_token = self.get_cookie("token")
            user_data = self.controller.users.get_user_by_api_token(api_token)

            logger.debug("Checking results")
            if user_data:
                # Login successful! Check perms
                logger.info(f"User {user_data['username']} has authenticated to API")

                return True  # This is to set the "authenticated"
            logging.debug("Auth unsuccessful")
            self.access_denied("unknown", "the user provided an invalid token")
            return False
        except Exception as e:
            logger.warning("An error occured while authenticating an API user: %s", e)
            self.finish(
                self.return_response(
                    403,
                    {
                        "error": "ACCESS_DENIED",
                        "info": "An error occured while authenticating the user",
                    },
                )
            )
            return False


class ServersStats(ApiHandler):
    def get(self):
        """Get details about all servers"""
        authenticated = self.authenticate_user()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)
        if not authenticated:
            return
        if user_obj["superuser"]:
            raw_stats = self.controller.servers.get_all_servers_stats()
        else:
            raw_stats = self.controller.servers.get_authorized_servers_stats(
                user_obj["user_id"]
            )
        stats = []
        for rs in raw_stats:
            s = {}
            for k, v in rs["server_data"].items():
                if isinstance(v, datetime):
                    s[k] = v.timestamp()
                else:
                    s[k] = v
            stats.append(s)

        # Get server stats
        # TODO Check perms
        self.finish(self.write({"servers": stats}))


class NodeStats(ApiHandler):
    def get(self):
        """Get stats for particular node"""
        authenticated = self.authenticate_user()
        if not authenticated:
            return

        # Get node stats
        node_stats = self.controller.servers.stats.get_node_stats()
        self.return_response(200, {"code": node_stats["node_stats"]})


class SendCommand(ApiHandler):
    def post(self):
        user = self.authenticate_user()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_uuid = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_uuid)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_uuid
        ):
            self.access_denied(user)
            return

        command = self.get_argument("command", default=None, strip=True)
        server_uuid = self.get_argument("id")
        if command:
            server = self.controller.servers.get_server_instance_by_id(server_uuid)
            if server.check_running:
                server.send_command(command)
                self.return_response(200, {"run": True})
            else:
                self.return_response(200, {"error": "SER_NOT_RUNNING"})
        else:
            self.return_response(200, {"error": "NO_COMMAND"})


class ServerBackup(ApiHandler):
    def post(self):
        user = self.authenticate_user()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_uuid = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_uuid)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if not self.permissions[
            "Backup"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_uuid
        ):
            self.access_denied(user)
            return

        server = self.controller.servers.get_server_instance_by_id(server_uuid)

        server.backup_server()

        self.return_response(200, {"code": "SER_BAK_CALLED"})


class StartServer(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        remote_ip = self.get_remote_ip()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_uuid = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_uuid)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return
        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_uuid
        ):
            self.access_denied("unknown")
            return

        server = self.controller.servers.get_server_instance_by_id(server_uuid)

        if not server.check_running():
            self.controller.management.send_command(
                user_obj["user_id"], server_uuid, remote_ip, "start_server"
            )
            self.return_response(200, {"code": "SER_START_CALLED"})
        else:
            self.return_response(500, {"error": "SER_RUNNING"})


class StopServer(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        remote_ip = self.get_remote_ip()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_uuid = self.get_argument("id")

        if (
            not user_obj["user_id"]
            in self.controller.server_perms.get_server_user_list(server_uuid)
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")

        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_uuid
        ):
            self.access_denied(user)
            return

        server = self.controller.servers.get_server_instance_by_id(server_uuid)

        if server.check_running():
            self.controller.management.send_command(
                user, server_uuid, remote_ip, "stop_server"
            )

            self.return_response(200, {"code": "SER_STOP_CALLED"})
        else:
            self.return_response(500, {"error": "SER_NOT_RUNNING"})


class RestartServer(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        remote_ip = self.get_remote_ip()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return
        server_uuid = self.get_argument("id")

        if not user_obj["user_id"] in self.controller.server_perms.get_server_user_list(
            server_uuid
        ):
            self.access_denied("unknown")

        if not self.permissions[
            "Commands"
        ] in self.controller.server_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token), server_uuid
        ):
            self.access_denied(user)

        self.controller.management.send_command(
            user, server_uuid, remote_ip, "restart_server"
        )
        self.return_response(200, {"code": "SER_RESTART_CALLED"})


class CreateUser(ApiHandler):
    def post(self):
        user = self.authenticate_user()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        user_perms = self.controller.crafty_perms.get_crafty_permissions_list(
            user_obj["user_id"]
        )
        if (
            not self.permissions["User_Config"] in user_perms
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if user is None:
            self.access_denied("unknown")
            return

        if not self.permissions[
            "User_Config"
        ] in self.controller.crafty_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token)
        ):
            self.access_denied(user)
            return

        new_username = self.get_argument("username").lower()
        new_pass = self.get_argument("password")
        manager = int(user_obj["user_id"])

        if new_username:
            self.controller.users.add_user(
                new_username, manager, new_pass, "default@example.com", True, False
            )

            self.return_response(
                200,
                {
                    "code": "COMPLETE",
                    "username": new_username,
                    "password": new_pass,
                },
            )
        else:
            self.return_response(
                500,
                {
                    "error": "MISSING_PARAMS",
                    "info": "Some paramaters failed validation",
                },
            )


class DeleteUser(ApiHandler):
    def post(self):
        user = self.authenticate_user()

        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        user_perms = self.controller.crafty_perms.get_crafty_permissions_list(
            user_obj["user_id"]
        )

        if (
            not self.permissions["User_Config"] in user_perms
            and not user_obj["superuser"]
        ):
            self.access_denied("unknown")
            return

        if user is None:
            self.access_denied("unknown")
            return

        if not self.permissions[
            "User_Config"
        ] in self.controller.crafty_perms.get_api_key_permissions_list(
            self.controller.users.get_api_key_by_token(self.api_token)
        ):
            self.access_denied(user)
            return

        user_id = self.get_argument("user_id", None, True)
        user_to_del = self.controller.users.get_user_by_id(user_id)

        if user_to_del["superuser"]:
            self.return_response(
                500,
                {"error": "NOT_ALLOWED", "info": "You cannot delete a super user"},
            )
        else:
            if user_id:
                self.controller.users.remove_user(user_id)
                self.return_response(200, {"code": "COMPLETED"})


class ListServers(ApiHandler):
    def get(self):
        user = self.authenticate_user()
        user_obj = self.controller.users.get_user_by_api_token(self.api_token)

        if user is None:
            self.access_denied("unknown")
            return

        if self.api_token is None:
            self.access_denied("unknown")
            return

        if user_obj["superuser"]:
            servers = self.controller.servers.get_all_defined_servers()
            servers = [str(i) for i in servers]
        else:
            servers = self.controller.servers.get_authorized_servers(
                user_obj["user_id"]
            )
            page_servers = []
            for server in servers:
                if server not in page_servers:
                    page_servers.append(
                        DatabaseShortcuts.get_data_obj(server.server_object)
                    )
            servers = page_servers
            servers = [str(i) for i in servers]

        self.return_response(
            200,
            {
                "code": "COMPLETED",
                "servers": servers,
            },
        )

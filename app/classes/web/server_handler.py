import json
import logging
import tornado.web
import tornado.escape

from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class ServerHandler(BaseHandler):
    def get_user_roles(self):
        user_roles = {}
        for user_id in self.controller.users.get_all_user_ids():
            user_roles_list = self.controller.users.get_user_roles_names(user_id)
            # user_servers =
            # self.controller.servers.get_authorized_servers(user.user_id)
            user_roles[user_id] = user_roles_list
        return user_roles

    @tornado.web.authenticated
    def get(self, page):
        (
            api_key,
            _token_data,
            exec_user,
        ) = self.current_user
        superuser = exec_user["superuser"]
        if api_key is not None:
            superuser = superuser and api_key.superuser

        if superuser:
            defined_servers = self.controller.servers.list_defined_servers()
            exec_user_role = {"Super User"}
            exec_user_crafty_permissions = (
                self.controller.crafty_perms.list_defined_crafty_permissions()
            )
            list_roles = []
            for role in self.controller.roles.get_all_roles():
                list_roles.append(self.controller.roles.get_role(role.role_id))
        else:
            exec_user_crafty_permissions = (
                self.controller.crafty_perms.get_crafty_permissions_list(
                    exec_user["user_id"]
                )
            )
            defined_servers = self.controller.servers.get_authorized_servers(
                exec_user["user_id"]
            )
            list_roles = []
            exec_user_role = set()
            for r in exec_user["roles"]:
                role = self.controller.roles.get_role(r)
                exec_user_role.add(role["role_name"])
                list_roles.append(self.controller.roles.get_role(role["role_id"]))

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

        template = "public/404.html"

        page_data = {
            "update_available": self.helper.update_available,
            "steamCMD": True,
            "windows": self.helper.is_os_windows(),
            "version_data": self.helper.get_version_string(),
            "user_data": exec_user,
            "user_role": exec_user_role,
            "online": Helpers.check_internet(),
            "roles": list_roles,
            "super_user": exec_user["superuser"],
            "user_crafty_permissions": exec_user_crafty_permissions,
            "crafty_permissions": {
                "Server_Creation": EnumPermissionsCrafty.SERVER_CREATION,
                "User_Config": EnumPermissionsCrafty.USER_CONFIG,
                "Roles_Config": EnumPermissionsCrafty.ROLES_CONFIG,
            },
            "server_stats": {
                "total": len(self.controller.servers.list_defined_servers()),
                "running": len(self.controller.servers.list_running_servers()),
                "stopped": (
                    len(self.controller.servers.list_defined_servers())
                    - len(self.controller.servers.list_running_servers())
                ),
            },
            "hosts_data": self.controller.management.get_latest_hosts_stats(),
            "menu_servers": page_servers,
            "show_contribute": self.helper.get_setting("show_contribute_link", True),
            "lang": self.controller.users.get_user_lang_by_id(exec_user["user_id"]),
            "lang_page": Helpers.get_lang_page(
                self.controller.users.get_user_lang_by_id(exec_user["user_id"])
            ),
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

        if superuser:
            page_data["roles"] = list_roles

        if page == "step1":
            if not superuser and not self.controller.crafty_perms.can_create_server(
                exec_user["user_id"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "not a server creator or server limit reached"
                )
                return
            page_data["server_api"] = False
            if page_data["online"]:
                page_data["server_api"] = self.helper.check_address_status(
                    "https://serverjars.com/api/fetchTypes"
                )
            page_data["server_types"] = self.controller.server_jars.get_serverjar_data()
            page_data["js_server_types"] = json.dumps(
                self.controller.server_jars.get_serverjar_data()
            )
            if page_data["server_types"] is None:
                page_data["server_types"] = []
                page_data["js_server_types"] = []
            template = "server/wizard.html"

        if page == "bedrock_step1":
            if not superuser and not self.controller.crafty_perms.can_create_server(
                exec_user["user_id"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "not a server creator or server limit reached"
                )
                return
            page_data["server_api"] = True
            template = "server/bedrock_wizard.html"

        if page == "steam_cmd_step1":
            if not superuser and not self.controller.crafty_perms.can_create_server(
                exec_user["user_id"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "not a server creator or server limit reached"
                )
                return

            page_data["servers"] = self.controller.steam_apps.fetch_cache()
            if page_data["servers"] is None:
                page_data["servers"] = []
            template = "server/steam_wizard.html"

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
        )

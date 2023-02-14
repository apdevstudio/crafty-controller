import json
import logging
import os
import time
import tornado.web
import tornado.escape
import bleach

from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.shared.helpers import Helpers
from app.classes.shared.file_helpers import FileHelpers
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

            template = "server/bedrock_wizard.html"

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
        )

    @tornado.web.authenticated
    def post(self, page):
        api_key, _token_data, exec_user = self.current_user
        superuser = exec_user["superuser"]
        if api_key is not None:
            superuser = superuser and api_key.superuser

        template = "public/404.html"
        page_data = {
            "version_data": "version_data_here",  # TODO
            "user_data": exec_user,
            "show_contribute": self.helper.get_setting("show_contribute_link", True),
            "background": self.controller.cached_login,
            "lang": self.controller.users.get_user_lang_by_id(exec_user["user_id"]),
            "lang_page": Helpers.get_lang_page(
                self.controller.users.get_user_lang_by_id(exec_user["user_id"])
            ),
        }

        if page == "command":
            server_id = bleach.clean(self.get_argument("id", None))
            command = bleach.clean(self.get_argument("command", None))

            if server_id is not None:
                if command == "clone_server":
                    if (
                        not superuser
                        and not self.controller.crafty_perms.can_create_server(
                            exec_user["user_id"]
                        )
                    ):
                        time.sleep(3)
                        self.helper.websocket_helper.broadcast_user(
                            exec_user["user_id"],
                            "send_start_error",
                            {
                                "error": "<i class='fas fa-exclamation-triangle'"
                                " style='font-size:48px;color:red'>"
                                "</i> Not a server creator or server limit reached."
                            },
                        )
                        return

                    def is_name_used(name):
                        for server in self.controller.servers.get_all_defined_servers():
                            if server["server_name"] == name:
                                return True
                        return

                    template = "/panel/dashboard"
                    server_data = self.controller.servers.get_server_data_by_id(
                        server_id
                    )
                    new_server_name = server_data.get("server_name") + " (Copy)"

                    name_counter = 1
                    while is_name_used(new_server_name):
                        name_counter += 1
                        new_server_name = (
                            server_data.get("server_name") + f" (Copy {name_counter})"
                        )

                    new_server_uuid = Helpers.create_uuid()
                    while os.path.exists(
                        os.path.join(self.helper.servers_dir, new_server_uuid)
                    ):
                        new_server_uuid = Helpers.create_uuid()
                    new_server_path = os.path.join(
                        self.helper.servers_dir, new_server_uuid
                    )

                    # copy the old server
                    FileHelpers.copy_dir(server_data.get("path"), new_server_path)

                    # TODO get old server DB data to individual variables
                    stop_command = server_data.get("stop_command")
                    new_server_command = str(server_data.get("execution_command"))
                    new_executable = server_data.get("executable")
                    new_server_log_file = str(
                        Helpers.get_os_understandable_path(server_data.get("log_path"))
                    )
                    backup_path = os.path.join(self.helper.backup_path, new_server_uuid)
                    server_port = server_data.get("server_port")
                    server_type = server_data.get("type")
                    created_by = exec_user["user_id"]

                    new_server_id = self.controller.servers.create_server(
                        new_server_name,
                        new_server_uuid,
                        new_server_path,
                        backup_path,
                        new_server_command,
                        new_executable,
                        new_server_log_file,
                        stop_command,
                        server_type,
                        created_by,
                        server_port,
                    )
                    if not exec_user["superuser"]:
                        new_server_uuid = self.controller.servers.get_server_data_by_id(
                            new_server_id
                        ).get("server_uuid")
                        role_id = self.controller.roles.add_role(
                            f"Creator of Server with uuid={new_server_uuid}",
                            exec_user["user_id"],
                        )
                        self.controller.server_perms.add_role_server(
                            new_server_id, role_id, "11111111"
                        )
                        self.controller.users.add_role_to_user(
                            exec_user["user_id"], role_id
                        )

                    self.controller.servers.init_all_servers()

                    return

                self.controller.management.send_command(
                    exec_user["user_id"], server_id, self.get_remote_ip(), command
                )

        if page == "step1":
            if not superuser and not self.controller.crafty_perms.can_create_server(
                exec_user["user_id"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "not a server creator or server limit reached"
                )
                return

            if not superuser:
                user_roles = self.controller.roles.get_all_roles()
            else:
                user_roles = self.get_user_roles()
            server = bleach.clean(self.get_argument("server", ""))
            server_name = bleach.clean(self.get_argument("server_name", ""))
            min_mem = bleach.clean(self.get_argument("min_memory", ""))
            max_mem = bleach.clean(self.get_argument("max_memory", ""))
            port = bleach.clean(self.get_argument("port", ""))
            if int(port) < 1 or int(port) > 65535:
                self.redirect(
                    "/panel/error?error=Constraint Error: "
                    "Port must be greater than 0 and less than 65535"
                )
                return
            import_type = bleach.clean(self.get_argument("create_type", ""))
            import_server_path = bleach.clean(self.get_argument("server_path", ""))
            import_server_jar = bleach.clean(self.get_argument("server_jar", ""))
            server_parts = server.split("|")
            captured_roles = []
            for role in user_roles:
                if bleach.clean(self.get_argument(str(role), "")) == "on":
                    captured_roles.append(role)

            if not server_name:
                self.redirect("/panel/error?error=Server name cannot be empty!")
                return

            if import_type == "import_jar":
                if self.helper.is_subdir(
                    import_server_path, self.controller.project_root
                ):
                    self.redirect(
                        "/panel/error?error=Loop Error: The selected path will cause"
                        " an infinite copy loop. Make sure Crafty's directory is not"
                        " in your server path."
                    )
                    return
                good_path = self.controller.verify_jar_server(
                    import_server_path, import_server_jar
                )

                if not good_path:
                    self.redirect(
                        "/panel/error?error=Server path or Server Jar not found!"
                    )
                    return

                new_server_id = self.controller.import_jar_server(
                    server_name,
                    import_server_path,
                    import_server_jar,
                    min_mem,
                    max_mem,
                    port,
                    exec_user["user_id"],
                )
                self.controller.management.add_to_audit_log(
                    exec_user["user_id"],
                    f'imported a jar server named "{server_name}"',
                    new_server_id,
                    self.get_remote_ip(),
                )
            elif import_type == "import_zip":
                # here import_server_path means the zip path
                zip_path = bleach.clean(self.get_argument("root_path"))
                good_path = Helpers.check_path_exists(zip_path)
                if not good_path:
                    self.redirect("/panel/error?error=Temp path not found!")
                    return

                new_server_id = self.controller.import_zip_server(
                    server_name,
                    zip_path,
                    import_server_jar,
                    min_mem,
                    max_mem,
                    port,
                    exec_user["user_id"],
                )
                if new_server_id == "false":
                    self.redirect(
                        f"/panel/error?error=Zip file not accessible! "
                        f"You can fix this permissions issue with "
                        f"sudo chown -R crafty:crafty {import_server_path} "
                        f"And sudo chmod 2775 -R {import_server_path}"
                    )
                    return
                self.controller.management.add_to_audit_log(
                    exec_user["user_id"],
                    f'imported a zip server named "{server_name}"',
                    new_server_id,
                    self.get_remote_ip(),
                )
            else:
                if len(server_parts) != 3:
                    self.redirect("/panel/error?error=Invalid server data")
                    return
                jar_type, server_type, server_version = server_parts
                # TODO: add server type check here and call the correct server
                # add functions if not a jar
                if server_type == "forge" and not self.helper.detect_java():
                    translation = self.helper.translation.translate(
                        "error",
                        "installerJava",
                        self.controller.users.get_user_lang_by_id(exec_user["user_id"]),
                    ).format(server_name)
                    self.redirect(f"/panel/error?error={translation}")
                    return
                new_server_id = self.controller.create_jar_server(
                    jar_type,
                    server_type,
                    server_version,
                    server_name,
                    min_mem,
                    max_mem,
                    port,
                    exec_user["user_id"],
                )
                self.controller.management.add_to_audit_log(
                    exec_user["user_id"],
                    f"created a {server_version} {str(server_type).capitalize()}"
                    f' server named "{server_name}"',
                    # Example: Admin created a 1.16.5 Bukkit server named "survival"
                    new_server_id,
                    self.get_remote_ip(),
                )

            # These lines create a new Role for the Server with full permissions
            # and add the user to it if he's not a superuser
            if len(captured_roles) == 0:
                if not superuser:
                    new_server_uuid = self.controller.servers.get_server_data_by_id(
                        new_server_id
                    ).get("server_uuid")
                    role_id = self.controller.roles.add_role(
                        f"Creator of Server with uuid={new_server_uuid}",
                        exec_user["user_id"],
                    )
                    self.controller.server_perms.add_role_server(
                        new_server_id, role_id, "11111111"
                    )
                    self.controller.users.add_role_to_user(
                        exec_user["user_id"], role_id
                    )

            else:
                for role in captured_roles:
                    role_id = role
                    self.controller.server_perms.add_role_server(
                        new_server_id, role_id, "11111111"
                    )

            self.controller.servers.stats.record_stats()
            self.redirect("/panel/dashboard")

        if page == "bedrock_step1":
            if not superuser and not self.controller.crafty_perms.can_create_server(
                exec_user["user_id"]
            ):
                self.redirect(
                    "/panel/error?error=Unauthorized access: "
                    "not a server creator or server limit reached"
                )
                return
            if not superuser:
                user_roles = self.controller.roles.get_all_roles()
            else:
                user_roles = self.controller.roles.get_all_roles()
            server = bleach.clean(self.get_argument("server", ""))
            server_name = bleach.clean(self.get_argument("server_name", ""))
            port = bleach.clean(self.get_argument("port", ""))

            if not port:
                port = 19132
            if int(port) < 1 or int(port) > 65535:
                self.redirect(
                    "/panel/error?error=Constraint Error: "
                    "Port must be greater than 0 and less than 65535"
                )
                return
            import_type = bleach.clean(self.get_argument("create_type", ""))
            import_server_path = bleach.clean(self.get_argument("server_path", ""))
            import_server_exe = bleach.clean(self.get_argument("server_jar", ""))
            server_parts = server.split("|")
            captured_roles = []
            for role in user_roles:
                if bleach.clean(self.get_argument(str(role), "")) == "on":
                    captured_roles.append(role)

            if not server_name:
                self.redirect("/panel/error?error=Server name cannot be empty!")
                return

            if import_type == "import_jar":
                if self.helper.is_subdir(
                    import_server_path, self.controller.project_root
                ):
                    self.redirect(
                        "/panel/error?error=Loop Error: The selected path will cause"
                        " an infinite copy loop. Make sure Crafty's directory is not"
                        " in your server path."
                    )
                    return
                good_path = self.controller.verify_jar_server(
                    import_server_path, import_server_exe
                )

                if not good_path:
                    self.redirect(
                        "/panel/error?error=Server path or Server Jar not found!"
                    )
                    return

                new_server_id = self.controller.import_bedrock_server(
                    server_name,
                    import_server_path,
                    import_server_exe,
                    port,
                    exec_user["user_id"],
                )
                self.controller.management.add_to_audit_log(
                    exec_user["user_id"],
                    f'imported a jar server named "{server_name}"',
                    new_server_id,
                    self.get_remote_ip(),
                )
            elif import_type == "import_zip":
                # here import_server_path means the zip path
                zip_path = bleach.clean(self.get_argument("root_path"))
                good_path = Helpers.check_path_exists(zip_path)
                if not good_path:
                    self.redirect("/panel/error?error=Temp path not found!")
                    return

                new_server_id = self.controller.import_bedrock_zip_server(
                    server_name,
                    zip_path,
                    import_server_exe,
                    port,
                    exec_user["user_id"],
                )
                if new_server_id == "false":
                    self.redirect(
                        f"/panel/error?error=Zip file not accessible! "
                        f"You can fix this permissions issue with"
                        f"sudo chown -R crafty:crafty {import_server_path} "
                        f"And sudo chmod 2775 -R {import_server_path}"
                    )
                    return
                self.controller.management.add_to_audit_log(
                    exec_user["user_id"],
                    f'imported a zip server named "{server_name}"',
                    new_server_id,
                    self.get_remote_ip(),
                )
            else:

                new_server_id = self.controller.create_bedrock_server(
                    server_name,
                    exec_user["user_id"],
                )
                self.controller.management.add_to_audit_log(
                    exec_user["user_id"],
                    "created a Bedrock " f'server named "{server_name}"',
                    # Example: Admin created a 1.16.5 Bukkit server named "survival"
                    new_server_id,
                    self.get_remote_ip(),
                )

            # These lines create a new Role for the Server with full permissions
            # and add the user to it if he's not a superuser
            if len(captured_roles) == 0:
                if not superuser:
                    new_server_uuid = self.controller.servers.get_server_data_by_id(
                        new_server_id
                    ).get("server_uuid")
                    role_id = self.controller.roles.add_role(
                        f"Creator of Server with uuid={new_server_uuid}",
                        exec_user["user_id"],
                    )
                    self.controller.server_perms.add_role_server(
                        new_server_id, role_id, "11111111"
                    )
                    self.controller.users.add_role_to_user(
                        exec_user["user_id"], role_id
                    )

            else:
                for role in captured_roles:
                    role_id = role
                    self.controller.server_perms.add_role_server(
                        new_server_id, role_id, "11111111"
                    )

            self.controller.servers.stats.record_stats()
            self.redirect("/panel/dashboard")

        try:
            self.render(
                template,
                data=page_data,
                translate=self.translator.translate,
            )
        except RuntimeError:
            self.redirect("/panel/dashboard")

import os
import logging
import bleach
import tornado.web
import tornado.escape

from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.shared.file_helpers import FileHelpers
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class FileHandler(BaseHandler):
    def render_page(self, template, page_data):
        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
        )

    @tornado.web.authenticated
    def get(self, page):
        api_key, _, exec_user = self.current_user
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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(
            exec_user["user_id"], server_id
        )

        if page == "get_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            file_path = Helpers.get_os_understandable_path(
                self.get_argument("file_path", None)
            )

            if not self.check_server_id(server_id, "get_file"):
                return
            server_id = bleach.clean(server_id)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                file_path,
            ) or not Helpers.check_file_exists(os.path.abspath(file_path)):
                logger.warning(
                    f"Invalid path in get_file file file ajax call ({file_path})"
                )
                Console.warning(
                    f"Invalid path in get_file file file ajax call ({file_path})"
                )
                return

            error = None

            try:
                with open(file_path, encoding="utf-8") as file:
                    file_contents = file.read()
            except UnicodeDecodeError:
                file_contents = ""
                error = "UnicodeDecodeError"

            self.write({"content": file_contents, "error": error})
            self.finish()

        elif page == "get_tree":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            path = self.get_argument("path", None)

            if not self.check_server_id(server_id, "get_tree"):
                return
            server_id = bleach.clean(server_id)

            if Helpers.validate_traversal(
                self.controller.servers.get_server_data_by_id(server_id)["path"], path
            ):
                self.write(
                    Helpers.get_os_understandable_path(path)
                    + "\n"
                    + self.helper.generate_tree(path)
                )
            self.finish()

        elif page == "get_dir":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            path = self.get_argument("path", None)

            if not self.check_server_id(server_id, "get_tree"):
                return
            server_id = bleach.clean(server_id)

            if Helpers.validate_traversal(
                self.controller.servers.get_server_data_by_id(server_id)["path"], path
            ):
                self.write(
                    Helpers.get_os_understandable_path(path)
                    + "\n"
                    + self.helper.generate_dir(path)
                )
            self.finish()

    @tornado.web.authenticated
    def post(self, page):
        api_key, _, exec_user = self.current_user
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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(
            exec_user["user_id"], server_id
        )

        if page == "create_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            file_parent = Helpers.get_os_understandable_path(
                self.get_body_argument("file_parent", default=None, strip=True)
            )
            file_name = self.get_body_argument("file_name", default=None, strip=True)
            file_path = os.path.join(file_parent, file_name)

            if not self.check_server_id(server_id, "create_file"):
                return
            server_id = bleach.clean(server_id)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                file_path,
            ) or Helpers.check_file_exists(os.path.abspath(file_path)):
                logger.warning(
                    f"Invalid path in create_file file ajax call ({file_path})"
                )
                Console.warning(
                    f"Invalid path in create_file file ajax call ({file_path})"
                )
                return

            # Create the file by opening it
            with open(file_path, "w", encoding="utf-8") as file_object:
                file_object.close()

        elif page == "create_dir":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            dir_parent = Helpers.get_os_understandable_path(
                self.get_body_argument("dir_parent", default=None, strip=True)
            )
            dir_name = self.get_body_argument("dir_name", default=None, strip=True)
            dir_path = os.path.join(dir_parent, dir_name)

            if not self.check_server_id(server_id, "create_dir"):
                return
            server_id = bleach.clean(server_id)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                dir_path,
            ) or Helpers.check_path_exists(os.path.abspath(dir_path)):
                logger.warning(
                    f"Invalid path in create_dir file ajax call ({dir_path})"
                )
                Console.warning(
                    f"Invalid path in create_dir file ajax call ({dir_path})"
                )
                return
            # Create the directory
            os.mkdir(dir_path)

        elif page == "unzip_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            path = Helpers.get_os_understandable_path(self.get_argument("path", None))
            if Helpers.is_os_windows():
                path = Helpers.wtol_path(path)
            FileHelpers.unzip_file(path)
            self.redirect(f"/panel/server_detail?id={server_id}&subpage=files")
            return

    @tornado.web.authenticated
    def delete(self, page):
        api_key, _, exec_user = self.current_user
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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(
            exec_user["user_id"], server_id
        )
        if page == "del_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            file_path = Helpers.get_os_understandable_path(
                self.get_body_argument("file_path", default=None, strip=True)
            )

            Console.warning(f"Delete {file_path} for server {server_id}")

            if not self.check_server_id(server_id, "del_file"):
                return
            server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not (
                Helpers.in_path(
                    Helpers.get_os_understandable_path(server_info["path"]), file_path
                )
                or Helpers.in_path(
                    Helpers.get_os_understandable_path(server_info["backup_path"]),
                    file_path,
                )
            ) or not Helpers.check_file_exists(os.path.abspath(file_path)):
                logger.warning(f"Invalid path in del_file file ajax call ({file_path})")
                Console.warning(
                    f"Invalid path in del_file file ajax call ({file_path})"
                )
                return

            # Delete the file
            FileHelpers.del_file(file_path)

        elif page == "del_dir":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            dir_path = Helpers.get_os_understandable_path(
                self.get_body_argument("dir_path", default=None, strip=True)
            )

            Console.warning(f"Delete {dir_path} for server {server_id}")

            if not self.check_server_id(server_id, "del_dir"):
                return
            server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not Helpers.in_path(
                Helpers.get_os_understandable_path(server_info["path"]), dir_path
            ) or not Helpers.check_path_exists(os.path.abspath(dir_path)):
                logger.warning(f"Invalid path in del_file file ajax call ({dir_path})")
                Console.warning(f"Invalid path in del_file file ajax call ({dir_path})")
                return

            # Delete the directory
            # os.rmdir(dir_path)     # Would only remove empty directories
            if Helpers.validate_traversal(
                Helpers.get_os_understandable_path(server_info["path"]), dir_path
            ):
                # Removes also when there are contents
                FileHelpers.del_dirs(dir_path)

    @tornado.web.authenticated
    def put(self, page):
        api_key, _, exec_user = self.current_user
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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(
            exec_user["user_id"], server_id
        )
        if page == "save_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            file_contents = self.get_body_argument(
                "file_contents", default=None, strip=True
            )
            file_path = Helpers.get_os_understandable_path(
                self.get_body_argument("file_path", default=None, strip=True)
            )

            if not self.check_server_id(server_id, "save_file"):
                return
            server_id = bleach.clean(server_id)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                file_path,
            ) or not Helpers.check_file_exists(os.path.abspath(file_path)):
                logger.warning(
                    f"Invalid path in save_file file ajax call ({file_path})"
                )
                Console.warning(
                    f"Invalid path in save_file file ajax call ({file_path})"
                )
                return

            # Open the file in write mode and store the content in file_object
            with open(file_path, "w", encoding="utf-8") as file_object:
                file_object.write(file_contents)

        elif page == "rename_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            item_path = Helpers.get_os_understandable_path(
                self.get_body_argument("item_path", default=None, strip=True)
            )
            new_item_name = self.get_body_argument(
                "new_item_name", default=None, strip=True
            )

            if not self.check_server_id(server_id, "rename_file"):
                return
            server_id = bleach.clean(server_id)

            if item_path is None or new_item_name is None:
                logger.warning("Invalid path(s) in rename_file file ajax call")
                Console.warning("Invalid path(s) in rename_file file ajax call")
                return

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                item_path,
            ) or not Helpers.check_path_exists(os.path.abspath(item_path)):
                logger.warning(
                    f"Invalid old name path in rename_file file ajax call ({server_id})"
                )
                Console.warning(
                    f"Invalid old name path in rename_file file ajax call ({server_id})"
                )
                return

            new_item_path = os.path.join(os.path.split(item_path)[0], new_item_name)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                new_item_path,
            ) or Helpers.check_path_exists(os.path.abspath(new_item_path)):
                logger.warning(
                    f"Invalid new name path in rename_file file ajax call ({server_id})"
                )
                Console.warning(
                    f"Invalid new name path in rename_file file ajax call ({server_id})"
                )
                return

            # RENAME
            os.rename(item_path, new_item_path)

    @tornado.web.authenticated
    def patch(self, page):
        api_key, _, exec_user = self.current_user
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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(
            exec_user["user_id"], server_id
        )
        if page == "rename_file":
            if not permissions["Files"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Files")
                    return
            item_path = Helpers.get_os_understandable_path(
                self.get_body_argument("item_path", default=None, strip=True)
            )
            new_item_name = self.get_body_argument(
                "new_item_name", default=None, strip=True
            )

            if not self.check_server_id(server_id, "rename_file"):
                return
            server_id = bleach.clean(server_id)

            if item_path is None or new_item_name is None:
                logger.warning("Invalid path(s) in rename_file file ajax call")
                Console.warning("Invalid path(s) in rename_file file ajax call")
                return

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                item_path,
            ) or not Helpers.check_path_exists(os.path.abspath(item_path)):
                logger.warning(
                    f"Invalid old name path in rename_file file ajax call ({server_id})"
                )
                Console.warning(
                    f"Invalid old name path in rename_file file ajax call ({server_id})"
                )
                return

            new_item_path = os.path.join(os.path.split(item_path)[0], new_item_name)

            if not Helpers.in_path(
                Helpers.get_os_understandable_path(
                    self.controller.servers.get_server_data_by_id(server_id)["path"]
                ),
                new_item_path,
            ) or Helpers.check_path_exists(os.path.abspath(new_item_path)):
                logger.warning(
                    f"Invalid new name path in rename_file file ajax call ({server_id})"
                )
                Console.warning(
                    f"Invalid new name path in rename_file file ajax call ({server_id})"
                )
                return

            # RENAME
            os.rename(item_path, new_item_path)

    def check_server_id(self, server_id, page_name):
        if server_id is None:
            logger.warning(
                f"Server ID not defined in {page_name} file ajax call ({server_id})"
            )
            Console.warning(
                f"Server ID not defined in {page_name} file ajax call ({server_id})"
            )
            return
        server_id = bleach.clean(server_id)

        # does this server id exist?
        if not self.controller.servers.server_id_exists(server_id):
            logger.warning(
                f"Server ID not found in {page_name} file ajax call ({server_id})"
            )
            Console.warning(
                f"Server ID not found in {page_name} file ajax call ({server_id})"
            )
            return
        return True

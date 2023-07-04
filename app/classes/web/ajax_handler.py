import os
import html
import pathlib
import re
import logging
import time
import urllib.parse
import bleach
import tornado.web
import tornado.escape

from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.shared.server import ServerOutBuf
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class AjaxHandler(BaseHandler):
    def render_page(self, template, page_data):
        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
        )

    @tornado.web.authenticated
    def get(self, page):
        _, _, exec_user = self.current_user
        error = bleach.clean(self.get_argument("error", "WTF Error!"))

        template = "panel/denied.html"

        page_data = {"user_data": exec_user, "error": error}

        if page == "error":
            template = "public/error.html"
            self.render_page(template, page_data)

        elif page == "server_log":
            server_id = self.get_argument("id", None)
            full_log = self.get_argument("full", False)

            if server_id is None:
                logger.warning("Server ID not found in server_log ajax call")
                self.redirect("/panel/error?error=Server ID Not Found")
                return

            server_id = bleach.clean(server_id)

            server_data = self.controller.servers.get_server_data_by_id(server_id)
            if not server_data:
                logger.warning("Server Data not found in server_log ajax call")
                self.redirect("/panel/error?error=Server ID Not Found")
                return

            if not server_data["log_path"]:
                logger.warning(
                    f"Log path not found in server_log ajax call ({server_id})"
                )

            if full_log:
                log_lines = self.helper.get_setting("max_log_lines")
                data = Helpers.tail_file(
                    # If the log path is absolute it returns it as is
                    # If it is relative it joins the paths below like normal
                    pathlib.Path(server_data["path"], server_data["log_path"]),
                    log_lines,
                )
            else:
                data = ServerOutBuf.lines.get(server_id, [])

            for line in data:
                try:
                    line = re.sub("(\033\\[(0;)?[0-9]*[A-z]?(;[0-9])?m?)", "", line)
                    line = re.sub("[A-z]{2}\b\b", "", line)
                    line = self.helper.log_colors(html.escape(line))
                    self.write(f"<span class='box'>{line}<br /></span>")
                    # self.write(d.encode("utf-8"))

                except Exception as e:
                    logger.warning(f"Skipping Log Line due to error: {e}")

        elif page == "announcements":
            data = Helpers.get_announcements()
            page_data["notify_data"] = data
            self.render_page("ajax/notify.html", page_data)

        elif page == "get_zip_tree":
            path = self.get_argument("path", None)

            self.write(
                Helpers.get_os_understandable_path(path)
                + "\n"
                + Helpers.generate_zip_tree(path)
            )
            self.finish()

        elif page == "get_zip_dir":
            path = self.get_argument("path", None)

            self.write(
                Helpers.get_os_understandable_path(path)
                + "\n"
                + Helpers.generate_zip_dir(path)
            )
            self.finish()

        elif page == "get_backup_tree":
            server_id = self.get_argument("id", None)
            folder = self.get_argument("path", None)

            output = ""

            dir_list = []
            unsorted_files = []
            file_list = os.listdir(folder)
            for item in file_list:
                if os.path.isdir(os.path.join(folder, item)):
                    dir_list.append(item)
                else:
                    unsorted_files.append(item)
            file_list = sorted(dir_list, key=str.casefold) + sorted(
                unsorted_files, key=str.casefold
            )
            output += f"""<ul class="tree-nested d-block" id="{folder}ul">"""
            for raw_filename in file_list:
                filename = html.escape(raw_filename)
                rel = os.path.join(folder, raw_filename)
                dpath = os.path.join(folder, filename)
                if str(dpath) in self.controller.management.get_excluded_backup_dirs(
                    server_id
                ):
                    if os.path.isdir(rel):
                        output += f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" class="checkBoxClass" name="root_path" value="{dpath}" checked>
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i style="color: var(--info);" class="far fa-folder"></i>
                            <i style="color: var(--info);" class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>
                            \n"""
                    else:
                        output += f"""<li
                        class="d-block tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' class="checkBoxClass" name='root_path' value="{dpath}" checked><span style="margin-right: 6px;">
                        <i class="far fa-file"></i></span></input>{filename}</li>"""

                else:
                    if os.path.isdir(rel):
                        output += f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" class="checkBoxClass" name="root_path" value="{dpath}">
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i style="color: var(--info);" class="far fa-folder"></i>
                            <i style="color: var(--info);" class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>
                            \n"""
                    else:
                        output += f"""<li
                        class="d-block tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' class="checkBoxClass" name='root_path' value="{dpath}">
                        <span style="margin-right: 6px;"><i class="far fa-file">
                        </i></span></input>{filename}</li>"""
            self.write(Helpers.get_os_understandable_path(folder) + "\n" + output)
            self.finish()

        elif page == "get_backup_dir":
            server_id = self.get_argument("id", None)
            folder = self.get_argument("path", None)
            output = ""

            dir_list = []
            unsorted_files = []
            file_list = os.listdir(folder)
            for item in file_list:
                if os.path.isdir(os.path.join(folder, item)):
                    dir_list.append(item)
                else:
                    unsorted_files.append(item)
            file_list = sorted(dir_list, key=str.casefold) + sorted(
                unsorted_files, key=str.casefold
            )
            output += f"""<ul class="tree-nested d-block" id="{folder}ul">"""
            for raw_filename in file_list:
                filename = html.escape(raw_filename)
                rel = os.path.join(folder, raw_filename)
                dpath = os.path.join(folder, filename)
                if str(dpath) in self.controller.management.get_excluded_backup_dirs(
                    server_id
                ):
                    if os.path.isdir(rel):
                        output += f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" name="root_path" value="{dpath}" checked>
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i class="far fa-folder"></i>
                            <i class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>"""
                    else:
                        output += f"""<li
                        class="tree-item tree-nested d-block tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' name='root_path' value='{dpath}' checked><span style="margin-right: 6px;">
                        <i class="far fa-file"></i></span></input>{filename}</li>"""

                else:
                    if os.path.isdir(rel):
                        output += f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" name="root_path" value="{dpath}">
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i class="far fa-folder"></i>
                            <i class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>"""
                    else:
                        output += f"""<li
                        class="tree-item tree-nested d-block tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' name='root_path' value='{dpath}'>
                        <span style="margin-right: 6px;"><i class="far fa-file">
                        </i></span></input>{filename}</li>"""

            self.write(Helpers.get_os_understandable_path(folder) + "\n" + output)
            self.finish()

        elif page == "get_dir":
            server_id = self.get_argument("id", None)
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
                    + Helpers.generate_dir(path)
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

        if page == "send_command":
            command = self.get_body_argument("command", default=None, strip=True)
            server_id = self.get_argument("id", None)

            if server_id is None:
                logger.warning("Server ID not found in send_command ajax call")
                Console.warning("Server ID not found in send_command ajax call")

            svr_obj = self.controller.servers.get_server_instance_by_id(server_id)

            if command == svr_obj.settings["stop_command"]:
                logger.info(
                    "Stop command detected as terminal input - intercepting."
                    + f"Starting Crafty's stop process for server with id: {server_id}"
                )
                self.controller.management.send_command(
                    exec_user["user_id"], server_id, self.get_remote_ip(), "stop_server"
                )
                command = None
            elif command == "restart":
                logger.info(
                    "Restart command detected as terminal input - intercepting."
                    + f"Starting Crafty's stop process for server with id: {server_id}"
                )
                self.controller.management.send_command(
                    exec_user["user_id"],
                    server_id,
                    self.get_remote_ip(),
                    "restart_server",
                )
                command = None
            if command:
                if svr_obj.check_running():
                    svr_obj.send_command(command)

            self.controller.management.add_to_audit_log(
                exec_user["user_id"],
                f"Sent command to "
                f"{self.controller.servers.get_server_friendly_name(server_id)} "
                f"terminal: {command}",
                server_id,
                self.get_remote_ip(),
            )

        elif page == "send_order":
            self.controller.users.update_server_order(
                exec_user["user_id"], bleach.clean(self.get_argument("order"))
            )
            return

        elif page == "backup_now":
            server_id = self.get_argument("id", None)
            if server_id is None:
                logger.error("Server ID is none. Canceling backup!")
                return

            server = self.controller.servers.get_server_instance_by_id(server_id)
            self.controller.management.add_to_audit_log_raw(
                self.controller.users.get_user_by_id(exec_user["user_id"])["username"],
                exec_user["user_id"],
                server_id,
                f"Backup now executed for server {server_id} ",
                source_ip=self.get_remote_ip(),
            )

            server.backup_server()

        elif page == "select_photo":
            if exec_user["superuser"]:
                photo = urllib.parse.unquote(self.get_argument("photo", ""))
                opacity = self.get_argument("opacity", 100)
                self.controller.management.set_login_opacity(int(opacity))
                if photo == "login_1.jpg":
                    self.controller.management.set_login_image("login_1.jpg")
                    self.controller.cached_login = f"{photo}"
                else:
                    self.controller.management.set_login_image(f"custom/{photo}")
                    self.controller.cached_login = f"custom/{photo}"
                return

        elif page == "delete_photo":
            if exec_user["superuser"]:
                photo = urllib.parse.unquote(self.get_argument("photo", None))
                if photo and photo != "login_1.jpg":
                    os.remove(
                        os.path.join(
                            self.controller.project_root,
                            f"app/frontend/static/assets/images/auth/custom/{photo}",
                        )
                    )
                    current = self.controller.cached_login
                    split = current.split("/")
                    if len(split) == 1:
                        current_photo = current
                    else:
                        current_photo = split[1]
                    if current_photo == photo:
                        self.controller.management.set_login_image("login_1.jpg")
                        self.controller.cached_login = "login_1.jpg"
            return

        elif page == "eula":
            server_id = self.get_argument("id", None)
            svr = self.controller.servers.get_server_instance_by_id(server_id)
            svr.agree_eula(exec_user["user_id"])

        elif page == "restore_backup":
            if not permissions["Backup"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Backups")
                    return
            server_id = bleach.clean(self.get_argument("id", None))
            zip_name = bleach.clean(self.get_argument("zip_file", None))
            svr_obj = self.controller.servers.get_server_obj(server_id)
            server_data = self.controller.servers.get_server_data_by_id(server_id)

            # import the server again based on zipfile
            if server_data["type"] == "minecraft-java":
                backup_path = svr_obj.backup_path
                if Helpers.validate_traversal(backup_path, zip_name):
                    temp_dir = Helpers.unzip_backup_archive(backup_path, zip_name)
                    new_server = self.controller.import_zip_server(
                        svr_obj.server_name,
                        temp_dir,
                        server_data["executable"],
                        "1",
                        "2",
                        server_data["server_port"],
                        server_data["created_by"],
                    )
                    new_server_id = new_server
                    new_server = self.controller.servers.get_server_data(new_server)
                    self.controller.rename_backup_dir(
                        server_id, new_server_id, new_server["server_uuid"]
                    )
                    # preserve current schedules
                    for schedule in self.controller.management.get_schedules_by_server(
                        server_id
                    ):
                        self.tasks_manager.update_job(
                            schedule.schedule_id, {"server_id": new_server_id}
                        )
                    # preserve execution command
                    new_server_obj = self.controller.servers.get_server_obj(
                        new_server_id
                    )
                    new_server_obj.execution_command = server_data["execution_command"]
                    # reset executable path
                    if svr_obj.path in svr_obj.executable:
                        new_server_obj.executable = str(svr_obj.executable).replace(
                            svr_obj.path, new_server_obj.path
                        )
                    # reset run command path
                    if svr_obj.path in svr_obj.execution_command:
                        new_server_obj.execution_command = str(
                            svr_obj.execution_command
                        ).replace(svr_obj.path, new_server_obj.path)
                    # reset log path
                    if svr_obj.path in svr_obj.log_path:
                        new_server_obj.log_path = str(svr_obj.log_path).replace(
                            svr_obj.path, new_server_obj.path
                        )
                    self.controller.servers.update_server(new_server_obj)

                    # preserve backup config
                    backup_config = self.controller.management.get_backup_config(
                        server_id
                    )
                    excluded_dirs = []
                    server_obj = self.controller.servers.get_server_obj(server_id)
                    loop_backup_path = self.helper.wtol_path(server_obj.path)
                    for item in self.controller.management.get_excluded_backup_dirs(
                        server_id
                    ):
                        item_path = self.helper.wtol_path(item)
                        bu_path = os.path.relpath(item_path, loop_backup_path)
                        bu_path = os.path.join(new_server_obj.path, bu_path)
                        excluded_dirs.append(bu_path)
                    self.controller.management.set_backup_config(
                        new_server_id,
                        new_server_obj.backup_path,
                        backup_config["max_backups"],
                        excluded_dirs,
                        backup_config["compress"],
                        backup_config["shutdown"],
                    )
                    # remove old server's tasks
                    try:
                        self.tasks_manager.remove_all_server_tasks(server_id)
                    except:
                        logger.info("No active tasks found for server")
                    self.controller.remove_server(server_id, True)
                    self.redirect("/panel/dashboard")

            else:
                backup_path = svr_obj.backup_path
                if Helpers.validate_traversal(backup_path, zip_name):
                    temp_dir = Helpers.unzip_backup_archive(backup_path, zip_name)
                    new_server = self.controller.import_bedrock_zip_server(
                        svr_obj.server_name,
                        temp_dir,
                        server_data["executable"],
                        server_data["server_port"],
                        server_data["created_by"],
                    )
                    new_server_id = new_server
                    new_server = self.controller.servers.get_server_data(new_server)
                    self.controller.rename_backup_dir(
                        server_id, new_server_id, new_server["server_uuid"]
                    )
                    # preserve current schedules
                    for schedule in self.controller.management.get_schedules_by_server(
                        server_id
                    ):
                        self.tasks_manager.update_job(
                            schedule.schedule_id, {"server_id": new_server_id}
                        )
                    # preserve execution command
                    new_server_obj = self.controller.servers.get_server_obj(
                        new_server_id
                    )
                    new_server_obj.execution_command = server_data["execution_command"]
                    # reset executable path
                    if server_obj.path in server_obj.executable:
                        new_server_obj.executable = str(server_obj.executable).replace(
                            server_obj.path, new_server_obj.path
                        )
                    # reset run command path
                    if server_obj.path in server_obj.execution_command:
                        new_server_obj.execution_command = str(
                            server_obj.execution_command
                        ).replace(server_obj.path, new_server_obj.path)
                    # reset log path
                    if server_obj.path in server_obj.log_path:
                        new_server_obj.log_path = str(server_obj.log_path).replace(
                            server_obj.path, new_server_obj.path
                        )
                    self.controller.servers.update_server(new_server_obj)

                    # preserve backup config
                    backup_config = self.controller.management.get_backup_config(
                        server_id
                    )
                    excluded_dirs = []
                    server_obj = self.controller.servers.get_server_obj(server_id)
                    loop_backup_path = self.helper.wtol_path(server_obj.path)
                    for item in self.controller.management.get_excluded_backup_dirs(
                        server_id
                    ):
                        item_path = self.helper.wtol_path(item)
                        bu_path = os.path.relpath(item_path, loop_backup_path)
                        bu_path = os.path.join(new_server_obj.path, bu_path)
                        excluded_dirs.append(bu_path)
                    self.controller.management.set_backup_config(
                        new_server_id,
                        new_server_obj.backup_path,
                        backup_config["max_backups"],
                        excluded_dirs,
                        backup_config["compress"],
                        backup_config["shutdown"],
                    )
                    try:
                        self.tasks_manager.remove_all_server_tasks(server_id)
                    except:
                        logger.info("No active tasks found for server")
                    self.controller.remove_server(server_id, True)
                    self.redirect("/panel/dashboard")

        elif page == "unzip_server":
            path = urllib.parse.unquote(self.get_argument("path", ""))
            if not path:
                path = os.path.join(
                    self.controller.project_root,
                    "imports",
                    urllib.parse.unquote(self.get_argument("file", "")),
                )
            if Helpers.check_file_exists(path):
                self.helper.unzip_server(path, exec_user["user_id"])
            else:
                user_id = exec_user["user_id"]
                if user_id:
                    time.sleep(5)
                    user_lang = self.controller.users.get_user_lang_by_id(user_id)
                    self.helper.websocket_helper.broadcast_user(
                        user_id,
                        "send_start_error",
                        {
                            "error": self.helper.translation.translate(
                                "error", "no-file", user_lang
                            )
                        },
                    )
            return

        elif page == "backup_select":
            path = self.get_argument("path", None)
            self.helper.backup_select(path, exec_user["user_id"])
            return

        elif page == "jar_cache":
            if not superuser:
                self.redirect("/panel/error?error=Not a super user")
                return

            self.controller.server_jars.manual_refresh_cache()
            return

        elif page == "update_server_dir":
            if self.helper.dir_migration:
                return
            for server in self.controller.servers.get_all_servers_stats():
                if server["stats"]["running"]:
                    self.helper.websocket_helper.broadcast_user(
                        exec_user["user_id"],
                        "send_start_error",
                        {
                            "error": "You must stop all servers before "
                            "starting a storage migration."
                        },
                    )
                    return
            if not superuser:
                self.redirect("/panel/error?error=Not a super user")
                return
            if self.helper.is_env_docker():
                self.redirect(
                    "/panel/error?error=This feature is not"
                    " supported on docker environments"
                )
                return
            new_dir = urllib.parse.unquote(self.get_argument("server_dir"))
            self.controller.update_master_server_dir(new_dir, exec_user["user_id"])
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

        if page == "del_backup":
            if not permissions["Backup"] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Backups")
                    return
            file_path = Helpers.get_os_understandable_path(
                self.get_body_argument("file_path", default=None, strip=True)
            )
            server_id = self.get_argument("id", None)

            Console.warning(f"Delete {file_path} for server {server_id}")

            if not self.check_server_id(server_id, "del_backup"):
                return
            server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not (
                self.helper.is_subdir(
                    file_path, Helpers.get_os_understandable_path(server_info["path"])
                )
                or self.helper.is_subdir(
                    file_path,
                    Helpers.get_os_understandable_path(server_info["backup_path"]),
                )
            ) or not Helpers.check_file_exists(os.path.abspath(file_path)):
                logger.warning(f"Invalid path in del_backup ajax call ({file_path})")
                Console.warning(f"Invalid path in del_backup ajax call ({file_path})")
                return

            # Delete the file
            if Helpers.validate_traversal(
                Helpers.get_os_understandable_path(server_info["backup_path"]),
                file_path,
            ):
                os.remove(file_path)

    def check_server_id(self, server_id, page_name):
        if server_id is None:
            logger.warning(
                f"Server ID not defined in {page_name} ajax call ({server_id})"
            )
            Console.warning(
                f"Server ID not defined in {page_name} ajax call ({server_id})"
            )
            return
        server_id = bleach.clean(server_id)

        # does this server id exist?
        if not self.controller.servers.server_id_exists(server_id):
            logger.warning(
                f"Server ID not found in {page_name} ajax call ({server_id})"
            )
            Console.warning(
                f"Server ID not found in {page_name} ajax call ({server_id})"
            )
            return
        return True

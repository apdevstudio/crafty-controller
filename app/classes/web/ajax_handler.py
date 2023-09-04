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

from app.classes.shared.file_helpers import FileHelpers
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

    @tornado.web.authenticated
    def post(self, page):
        api_key, _, exec_user = self.current_user
        superuser = exec_user["superuser"]
        if api_key is not None:
            superuser = superuser and api_key.superuser

        if page == "select_photo":
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

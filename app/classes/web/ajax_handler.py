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

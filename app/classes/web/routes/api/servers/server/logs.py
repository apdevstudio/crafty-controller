import html
import logging
import re
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.shared.server import ServerOutBuf
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiServersServerLogsHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        # GET /api/v2/servers/server/logs?file=true
        read_log_file = self.get_query_argument("file", None) == "true"
        # GET /api/v2/servers/server/logs?colors=true
        colored_output = self.get_query_argument("colors", None) == "true"
        # GET /api/v2/servers/server/logs?raw=true
        disable_ansi_strip = self.get_query_argument("raw", None) == "true"
        # GET /api/v2/servers/server/logs?html=true
        use_html = self.get_query_argument("html", None) == "true"

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        if (
            EnumPermissionsServer.LOGS
            not in self.controller.server_perms.get_user_id_permissions_list(
                auth_data[4]["user_id"], server_id
            )
        ):
            # if the user doesn't have Logs permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        server_data = self.controller.servers.get_server_data_by_id(server_id)

        if read_log_file:
            log_lines = self.helper.get_setting("max_log_lines")
            raw_lines = self.helper.tail_file(
                self.helper.get_os_understandable_path(server_data["log_path"]),
                log_lines,
            )
        else:
            raw_lines = ServerOutBuf.lines.get(server_id, [])

        lines = []

        for line in raw_lines:
            try:
                if not disable_ansi_strip:
                    line = re.sub(
                        "(\033\\[(0;)?[0-9]*[A-z]?(;[0-9])?m?)|(> )", "", line
                    )
                    line = re.sub("[A-z]{2}\b\b", "", line)
                    line = html.escape(line)

                if colored_output:
                    line = self.helper.log_colors(line)

                lines.append(line)
            except Exception as e:
                logger.warning(f"Skipping Log Line due to error: {e}")

        if use_html:
            for line in lines:
                self.write(f"{line}<br />")
        else:
            self.finish_json(200, {"status": "ok", "data": lines})

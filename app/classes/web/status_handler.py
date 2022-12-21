import logging

from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class StatusHandler(BaseHandler):
    def get(self):
        page_data = {"background": self.controller.cached_login}
        page_data["lang"] = self.helper.get_setting("language")
        page_data["lang_page"] = self.helper.get_lang_page(
            self.helper.get_setting("language")
        )
        page_data["servers"] = self.controller.servers.get_all_servers_stats()
        running = 0
        for srv in page_data["servers"]:
            if srv["stats"]["running"]:
                running += 1
            server_data = srv.get("server_data", False)
            server_id = server_data.get("server_id", False)
            srv["raw_ping_result"] = self.controller.servers.get_server_stats_by_id(
                server_id
            )
            if "icon" not in srv["raw_ping_result"]:
                srv["raw_ping_result"]["icon"] = False

        page_data["running"] = running

        template = "public/status.html"

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
        )

    def post(self):
        page_data = {}
        page_data["servers"] = self.controller.servers.get_all_servers_stats()
        for srv in page_data["servers"]:
            server_data = srv.get("server_data", False)
            server_id = server_data.get("server_id", False)
            srv["raw_ping_result"] = self.controller.servers.get_server_stats_by_id(
                server_id
            )
        template = "public/status.html"

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
        )

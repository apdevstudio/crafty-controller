import sys
import json
import logging

from app.classes.shared.console import console
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.controller import controller
from app.classes.shared.models import db_helper, Servers
from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.minecraft.stats import stats
from app.classes.shared.helpers import helper


logger = logging.getLogger(__name__)

try:
    import tornado.web
    import tornado.escape
    import bleach

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class ServerHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self, page):
        # name = tornado.escape.json_decode(self.current_user)
        user_data = json.loads(self.get_secure_cookie("user_data"))

        template = "public/404.html"

        defined_servers = controller.list_defined_servers()

        page_data = {
            'version_data': helper.get_version_string(),
            'user_data': user_data,
            'server_stats': {
                'total': len(controller.list_defined_servers()),
                'running': len(controller.list_running_servers()),
                'stopped': (len(controller.list_defined_servers()) - len(controller.list_running_servers()))
            },
            'hosts_data': db_helper.get_latest_hosts_stats(),
            'menu_servers': defined_servers,
            'show_contribute': helper.get_setting("show_contribute_link", True)
        }

        if page == "step1":

            page_data['server_types'] = server_jar_obj.get_serverjar_data()
            template = "server/wizard.html"

        self.render(
            template,
            data=page_data
        )

    @tornado.web.authenticated
    def post(self, page):

        user_data = json.loads(self.get_secure_cookie("user_data"))

        template = "public/404.html"
        page_data = {
            'version_data': "version_data_here",
            'user_data': user_data,
            'show_contribute': helper.get_setting("show_contribute_link", True)
        }

        if page == "command":
            server_id = bleach.clean(self.get_argument("id", None))
            command = bleach.clean(self.get_argument("command", None))

            if server_id is not None:
                db_helper.send_command(user_data['user_id'], server_id, self.get_remote_ip(), command)

        if page == "step1":

            server = bleach.clean(self.get_argument('server', ''))
            server_name = bleach.clean(self.get_argument('server_name', ''))
            min_mem = bleach.clean(self.get_argument('min_memory', ''))
            max_mem = bleach.clean(self.get_argument('max_memory', ''))
            port = bleach.clean(self.get_argument('port', ''))
            import_type = bleach.clean(self.get_argument('create_type', ''))
            import_server_path = bleach.clean(self.get_argument('server_path', ''))
            import_server_jar = bleach.clean(self.get_argument('server_jar', ''))
            server_parts = server.split("|")

            if import_type == 'import_jar':
                good_path = controller.verify_jar_server(import_server_path, import_server_jar)

                if not good_path:
                    self.redirect("/panel/error?error=Server path or Server Jar not found!")
                    return False

                new_server_id = controller.import_jar_server(server_name, import_server_path,import_server_jar, min_mem, max_mem, port)
            elif import_type == 'import_zip':
                good_path = controller.verify_zip_server(import_server_path)
                if not good_path:
                    self.redirect("/panel/error?error=Zip file not found!")
                    return False

                new_server_id = controller.import_zip_server(server_name, import_server_path,import_server_jar, min_mem, max_mem, port)
                if new_server_id == "false":
                    self.redirect("/panel/error?error=ZIP file not accessible! You can fix this permissions issue with sudo chown -R crafty:crafty {} And sudo chmod 2775 -R {}".format(import_server_path, import_server_path))
                    return False
            else:
                # todo: add server type check here and call the correct server add functions if not a jar
                new_server_id = controller.create_jar_server(server_parts[0], server_parts[1], server_name, min_mem, max_mem, port)

            if new_server_id:
                db_helper.add_to_audit_log(user_data['user_id'],
                                           "created a {} {} server named \"{}\"".format(server_parts[1], str(server_parts[0]).capitalize(), server_name), # Example: Admin created a 1.16.5 Bukkit server named "survival"
                                           new_server_id,
                                           self.get_remote_ip())
            else:
                logger.error("Unable to create server")
                console.error("Unable to create server")

            stats.record_stats()
            self.redirect("/panel/dashboard")

        self.render(
            template,
            data=page_data
        )
import json
import logging
import asyncio
from urllib.parse import parse_qsl
import tornado.websocket

from app.classes.shared.main_controller import Controller
from app.classes.shared.helpers import Helpers
from app.classes.shared.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class BaseSocketHandler(tornado.websocket.WebSocketHandler):
    ws_authorized_pages = {}  # Must be overridden at init
    ws_authorized_events = {}  # Must be overridden at init
    page = None
    page_query_params = None
    controller: Controller = None
    tasks_manager = None
    translator = None
    io_loop = None

    def initialize(
        self,
        helper=None,
        controller=None,
        tasks_manager=None,
        translator=None,
        file_helper=None,
    ):
        self.helper = helper
        self.controller = controller
        self.tasks_manager = tasks_manager
        self.translator = translator
        self.file_helper = file_helper
        self.io_loop = tornado.ioloop.IOLoop.current()

    def get_remote_ip(self):
        remote_ip = (
            self.request.headers.get("X-Real-IP")
            or self.request.headers.get("X-Forwarded-For")
            or self.request.remote_ip
        )
        return remote_ip

    # pylint: disable=arguments-differ
    def open(self):
        """
        This method must be overridden
        """
        raise NotImplementedError

    def handle(self):
        """
        This method must be overridden
        """
        raise NotImplementedError

    def get_user_id(self):
        """
        This method must be overridden
        """
        raise NotImplementedError

    def check_auth(self):
        """
        This method must be overridden
        """
        raise NotImplementedError

    # pylint: disable=arguments-renamed
    def on_message(self, raw_message):
        logger.debug(f"Got message from WebSocket connection {raw_message}")
        message = json.loads(raw_message)
        logger.debug(f"Event Type: {message['event']}, Data: {message['data']}")

    def on_close(self):
        WebSocketManager().remove_client(self)
        logger.debug("Closed WebSocket connection")

    async def write_message_int(self, message):
        self.write_message(message)

    def write_message_async(self, message):
        asyncio.run_coroutine_threadsafe(
            self.write_message_int(message), self.io_loop.asyncio_loop
        )

    def send_message(self, event_type: str, data):
        message = str(json.dumps({"event": event_type, "data": data}))
        self.write_message_async(message)

    def check_policy(self, event_type: str):
        # Looking if the client is the right one for the page
        if self.page.split("/")[1] not in self.ws_authorized_pages:
            return False
        # Looking if the event is send to the right page
        if event_type not in self.ws_authorized_events:
            return False
        # All seams good so we can agree
        return True


class SocketHandler(BaseSocketHandler):
    ws_authorized_pages = {"panel", "server", "ajax", "files", "upload", "api"}
    ws_authorized_events = {
        "notification",
        "update_host_stats",
        "update_server_details",
        "update_server_status",
        "send_start_reload",
        "send_start_error",
        # TODO "send_temp_path",
        "support_status_update",
        "send_logs_bootbox",
        "move_status",
        "vterm_new_line",
        "send_eula_bootbox",
        "backup_reload",
        "backup_status",
        "update_button_status",
        "remove_spinner",
        "close_upload_box",
    }  # Must be overridden at init

    def get_user_id(self):
        _, _, user = self.controller.authentication.check(self.get_cookie("token"))
        return user["user_id"]

    def check_auth(self):
        return self.controller.authentication.check_bool(self.get_cookie("token"))

    # pylint: disable=arguments-differ
    def open(self):
        logger.debug("Checking WebSocket authentication")
        if self.check_auth():
            self.handle()
        else:
            WebSocketManager().broadcast_to_admins(
                self, "notification", "Not authenticated for WebSocket connection"
            )
            self.close(1011, "Forbidden WS Access")
            self.controller.management.add_to_audit_log_raw(
                "unknown",
                0,
                0,
                "Someone tried to connect via WebSocket without proper authentication",
                self.get_remote_ip(),
            )
            WebSocketManager().broadcast(
                "notification",
                "Someone tried to connect via WebSocket without proper authentication",
            )
            logger.warning(
                "Someone tried to connect via WebSocket without proper authentication"
            )

    def handle(self):
        self.page = self.get_query_argument("page")
        self.page_query_params = dict(
            parse_qsl(
                Helpers.remove_prefix(self.get_query_argument("page_query_params"), "?")
            )
        )
        WebSocketManager().add_client(self)
        logger.debug("Opened WebSocket connection")

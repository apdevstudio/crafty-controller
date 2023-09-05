import json
import logging
import asyncio
from urllib.parse import parse_qsl
import tornado.websocket

from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)


class SocketHandler(tornado.websocket.WebSocketHandler):
    page = None
    page_query_params = None
    controller = None
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
            self.helper.websocket_helper.send_message(
                self, "notification", "Not authenticated for WebSocket connection"
            )
            self.close()
            self.controller.management.add_to_audit_log_raw(
                "unknown",
                0,
                0,
                "Someone tried to connect via WebSocket without proper authentication",
                self.get_remote_ip(),
            )
            self.helper.websocket_helper.broadcast(
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
        self.helper.websocket_helper.add_client(self)
        logger.debug("Opened WebSocket connection")

    # pylint: disable=arguments-renamed
    @staticmethod
    def on_message(raw_message):
        logger.debug(f"Got message from WebSocket connection {raw_message}")
        message = json.loads(raw_message)
        logger.debug(f"Event Type: {message['event']}, Data: {message['data']}")

    def on_close(self):
        self.helper.websocket_helper.remove_client(self)
        logger.debug("Closed WebSocket connection")

    async def write_message_int(self, message):
        self.write_message(message)

    def write_message_helper(self, message):
        asyncio.run_coroutine_threadsafe(
            self.write_message_int(message), self.io_loop.asyncio_loop
        )

import json
import logging
import asyncio
import sys

from urllib.parse import parse_qsl
from app.classes.models.users import Users
from app.classes.shared.authentication import authentication
from app.classes.shared.helpers import helper
from app.classes.web.websocket_helper import websocket_helper
from app.classes.shared.console import console

logger = logging.getLogger(__name__)

try:
    import tornado.websocket

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class SocketHandler(tornado.websocket.WebSocketHandler):
    page = None
    page_query_params = None
    controller = None
    tasks_manager = None
    translator = None
    io_loop = None

    def initialize(self, controller=None, tasks_manager=None, translator=None):
        self.controller = controller
        self.tasks_manager = tasks_manager
        self.translator = translator
        self.io_loop = tornado.ioloop.IOLoop.current()

    def get_remote_ip(self):
        remote_ip = self.request.headers.get("X-Real-IP") or \
                    self.request.headers.get("X-Forwarded-For") or \
                    self.request.remote_ip
        return remote_ip

    def get_user_id(self):
        _, _, user = authentication.check(self.get_cookie('token'))
        return user.user_id

    def check_auth(self):
        return authentication.check_bool(self.get_cookie('token'))

    def open(self):
        logger.debug('Checking WebSocket authentication')
        if self.check_auth():
            self.handle()
        else:
            websocket_helper.send_message(self, 'notification', 'Not authenticated for WebSocket connection')
            self.close()
            self.controller.management.add_to_audit_log_raw('unknown', 0, 0, 'Someone tried to connect via WebSocket without proper authentication', self.get_remote_ip())
            websocket_helper.broadcast('notification', 'Someone tried to connect via WebSocket without proper authentication')
            logger.warning('Someone tried to connect via WebSocket without proper authentication')

    def handle(self):
        self.page = self.get_query_argument('page')
        self.page_query_params = dict(parse_qsl(helper.remove_prefix(
            self.get_query_argument('page_query_params'),
            '?'
        )))
        websocket_helper.add_client(self)
        logger.debug('Opened WebSocket connection')
        # websocket_helper.broadcast('notification', 'New client connected')

    @staticmethod
    def on_message(raw_message):

        logger.debug('Got message from WebSocket connection {}'.format(raw_message))
        message = json.loads(raw_message)
        logger.debug('Event Type: {}, Data: {}'.format(message['event'], message['data']))

    def on_close(self):
        websocket_helper.remove_client(self)
        logger.debug('Closed WebSocket connection')
        # websocket_helper.broadcast('notification', 'Client disconnected')

    async def write_message_int(self, message):
        self.write_message(message)
    
    def write_message_helper(self, message):
        asyncio.run_coroutine_threadsafe(self.write_message_int(message), self.io_loop.asyncio_loop)


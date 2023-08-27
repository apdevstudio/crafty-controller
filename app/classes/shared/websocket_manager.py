import json
import logging
from enum import Enum

from app.classes.shared.singleton import Singleton
from app.classes.shared.console import Console
from app.classes.models.users import HelperUsers

logger = logging.getLogger(__name__)


class EnumWebSocketState(Enum):
    WS_UNKNOWN = -1
    WS_PUBLIC = 0
    WS_USER_AUTH = 1


class WebSocketManager(metaclass=Singleton):
    def __init__(self):
        self.auth_clients = set()
        self.public_clients = set()

    def add_client(self, client):
        if client.ws_state == EnumWebSocketState.WS_PUBLIC:
            self.public_clients.add(client)
        elif client.ws_state == EnumWebSocketState.WS_USER_AUTH:
            self.auth_clients.add(client)
        else:
            logging.debug("Unknown WebSocket")
            client.close()

    def remove_client(self, client):
        if client.ws_state == EnumWebSocketState.WS_PUBLIC:
            self.public_clients.remove(client)
        elif client.ws_state == EnumWebSocketState.WS_USER_AUTH:
            self.auth_clients.remove(client)

    def broadcast(self, event_type: str, data):
        logger.debug(
            f"Sending to {len(self.public_clients | self.auth_clients)} clients: "
            f"{json.dumps({'event': event_type, 'data': data})}"
        )
        for client in self.public_clients | self.auth_clients:
            try:
                client.send_message(event_type, data)
            except Exception as e:
                logger.exception(
                    f"Error caught while sending WebSocket message to "
                    f"{client.get_remote_ip()} {e}"
                )

    def broadcast_to_admins(self, event_type: str, data):
        def filter_fn(client):
            if client.get_user_id in HelperUsers.get_super_user_list():
                return True
            return False

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_page(self, page: str, event_type: str, data):
        def filter_fn(client):
            return client.check_policy(event_type) and client.page == page

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_user(self, user_id: str, event_type: str, data):
        def filter_fn(client):
            return client.get_user_id() == user_id

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_user_page(self, page: str, user_id: str, event_type: str, data):
        def filter_fn(client):
            if client.get_user_id() != user_id:
                return False
            if client.page != page:
                return False
            return True

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_user_page_params(
        self, page: str, params: dict, user_id: str, event_type: str, data
    ):
        def filter_fn(client):
            if client.get_user_id() != user_id:
                return False
            if client.page != page:
                return False
            for key, param in params.items():
                if param != client.page_query_params.get(key, None):
                    return False
            return True

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_page_params(self, page: str, params: dict, event_type: str, data):
        def filter_fn(client):
            if client.page != page:
                return False
            for key, param in params.items():
                if param != client.page_query_params.get(key, None):
                    return False
            return True

        self.broadcast_with_fn(filter_fn, event_type, data)

    def broadcast_with_fn(self, filter_fn, event_type: str, data):
        # assign self.clients to a static variable here so hopefully
        # the set size won't change
        static_clients = self.public_clients | self.auth_clients
        clients = list(filter(filter_fn, static_clients))
        logger.debug(
            f"Sending to {len(clients)}  \
            out of {len(self.public_clients | self.auth_clients)} "
            f"clients: {json.dumps({'event': event_type, 'data': data})}"
        )

        for client in clients[:]:
            try:
                client.send_message(event_type, data)
            except Exception as e:
                logger.exception(
                    f"Error catched while sending WebSocket message to "
                    f"{client.get_remote_ip()} {e}"
                )

    def disconnect_all(self):
        Console.info("Disconnecting WebSocket clients")
        for client in self.public_clients | self.auth_clients:
            client.close()
        Console.info("Disconnected WebSocket clients")

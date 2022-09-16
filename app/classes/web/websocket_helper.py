import json
import logging

from app.classes.shared.console import Console

logger = logging.getLogger(__name__)


class WebSocketHelper:
    def __init__(self, helper):
        self.helper = helper
        self.clients = set()

    def add_client(self, client):
        self.clients.add(client)

    def remove_client(self, client):
        self.clients.remove(client)

    def send_message(self, client, event_type: str, data):
        if client.check_auth():
            message = str(json.dumps({"event": event_type, "data": data}))
            client.write_message_helper(message)

    def broadcast(self, event_type: str, data):
        logger.debug(
            f"Sending to {len(self.clients)} clients: "
            f"{json.dumps({'event': event_type, 'data': data})}"
        )
        for client in self.clients[:]:
            try:
                self.send_message(client, event_type, data)
            except Exception as e:
                logger.exception(
                    f"Error caught while sending WebSocket message to "
                    f"{client.get_remote_ip()} {e}"
                )

    def broadcast_page(self, page: str, event_type: str, data):
        def filter_fn(client):
            return client.page == page

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
        clients = list(filter(filter_fn, self.clients))
        logger.debug(
            f"Sending to {len(clients)} out of {len(self.clients)} "
            f"clients: {json.dumps({'event': event_type, 'data': data})}"
        )

        for client in clients[:]:
            try:
                self.send_message(client, event_type, data)
            except Exception as e:
                logger.exception(
                    f"Error catched while sending WebSocket message to "
                    f"{client.get_remote_ip()} {e}"
                )

    def disconnect_all(self):
        Console.info("Disconnecting WebSocket clients")
        for client in self.clients:
            client.close()
        Console.info("Disconnected WebSocket clients")

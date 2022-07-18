# TODO: create and read

import logging

from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)


class ApiServersServerTasksIndexHandler(BaseApiHandler):
    def get(self, server_id: str, task_id: str):
        pass

    def post(self, server_id: str, task_id: str):
        pass

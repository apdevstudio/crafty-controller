import logging
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)


class ApiUsersUserPfpHandler(BaseApiHandler):
    def get(self, user_id):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if user_id == "@me":
            user = auth_data[4]
        else:
            user = self.controller.users.get_user_by_id(user_id)

        logger.debug(
            f'User {auth_data[4]["user_id"]} is fetching the pfp for user {user_id}'
        )

        self.finish_json(200, {"status": "ok", "data": user["pfp"]})
        return

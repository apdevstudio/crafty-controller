import logging
import libgravatar
import requests
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

        # http://en.gravatar.com/site/implement/images/#rating
        if self.helper.get_setting("allow_nsfw_profile_pictures"):
            rating = "x"
        else:
            rating = "g"

        # Get grvatar hash for profile pictures
        if (
            not self.helper.check_internet()
            or user["email"] != "default@example.com"
            or user["email"] != ""
        ):
            gravatar = libgravatar.Gravatar(libgravatar.sanitize_email(user["email"]))
            url = gravatar.get_image(
                size=80,
                default="404",
                force_default=False,
                rating=rating,
                filetype_extension=False,
                use_ssl=True,
            )
            try:
                requests.head(url).raise_for_status()
            except requests.HTTPError as e:
                logger.debug("Gravatar profile picture not found", exc_info=e)
            else:
                self.finish_json(200, {"status": "ok", "data": url})
                return

        self.finish_json(200, {"status": "ok", "data": None})

import logging
import time
from typing import Optional, Dict, Any, Tuple
import jwt
from jwt import PyJWTError

from app.classes.models.users import HelperUsers, ApiKeys
from app.classes.controllers.management_controller import ManagementController

logger = logging.getLogger(__name__)


class Authentication:
    def __init__(self, helper):
        self.helper = helper
        try:
            self.secret = ManagementController.get_crafty_api_key()
            if self.secret == "":
                self.secret = self.helper.random_string_generator(64)
                ManagementController.set_crafty_api_key(str(self.secret))
        except:
            self.secret = self.helper.random_string_generator(64)
            ManagementController.set_crafty_api_key(str(self.secret))

    def generate(self, user_id, extra=None):
        if extra is None:
            extra = {}
        jwt_encoded = jwt.encode(
            {"user_id": user_id, "iat": int(time.time()), **extra},
            self.secret,
            algorithm="HS256",
        )
        return jwt_encoded

    def read(self, token):
        return jwt.decode(token, self.secret, algorithms=["HS256"])

    def check_no_iat(self, token) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(str(token), self.secret, algorithms=["HS256"])
        except PyJWTError as error:
            logger.debug("Error while checking JWT token: ", exc_info=error)
            return None

    def check(
        self,
        token,
    ) -> Optional[Tuple[Optional[ApiKeys], Dict[str, Any], Dict[str, Any]]]:
        try:
            data = jwt.decode(str(token), self.secret, algorithms=["HS256"])
        except PyJWTError as error:
            logger.debug("Error while checking JWT token: ", exc_info=error)
            return None
        iat: int = data["iat"]
        key: Optional[ApiKeys] = None
        if "token_id" in data:
            key_id = data["token_id"]
            key = HelperUsers.get_user_api_key(key_id)
            if key is None:
                return None
        user_id: str = data["user_id"]
        user = HelperUsers.get_user(user_id)
        # TODO: Have a cache or something so we don't constantly
        # have to query the database
        if int(user.get("valid_tokens_from").timestamp()) < iat:
            # Success!
            return key, data, user
        return None

    def check_err(
        self,
        token,
    ) -> Tuple[Optional[ApiKeys], Dict[str, Any], Dict[str, Any]]:
        # Without this function there would be runtime exceptions like the following:
        # "None" object is not iterable

        output = self.check(token)
        if output is None:
            raise Exception("Invalid token")
        return output

    def check_bool(self, token) -> bool:
        return self.check(token) is not None

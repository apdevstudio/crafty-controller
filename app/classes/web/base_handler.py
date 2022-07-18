import logging
import re
import typing as t
import orjson
import bleach
import tornado.web

from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.models.users import ApiKeys
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_controller import Controller
from app.classes.shared.translation import Translation
from app.classes.models.management import DatabaseShortcuts

logger = logging.getLogger(__name__)

bearer_pattern = re.compile(r"^Bearer ", flags=re.IGNORECASE)


class BaseHandler(tornado.web.RequestHandler):
    nobleach = {bool, type(None)}
    redactables = ("pass", "api")

    helper: Helpers
    controller: Controller
    translator: Translation

    # noinspection PyAttributeOutsideInit
    def initialize(
        self, helper=None, controller=None, tasks_manager=None, translator=None
    ):
        self.helper = helper
        self.controller = controller
        self.tasks_manager = tasks_manager
        self.translator = translator

    def set_default_headers(self) -> None:
        """
        Fix CORS
        """
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header(
            "Access-Control-Allow-Headers",
            "Content-Type, x-requested-with, Authorization",
        )
        self.set_header(
            "Access-Control-Allow-Methods", "POST, GET, PUT, DELETE, OPTIONS"
        )

    def options(self, *_, **__):
        """
        Fix CORS
        """
        # no body
        self.set_status(204)
        self.finish()

    def get_remote_ip(self):
        remote_ip = (
            self.request.headers.get("X-Real-IP")
            or self.request.headers.get("X-Forwarded-For")
            or self.request.remote_ip
        )
        return remote_ip

    current_user: t.Tuple[t.Optional[ApiKeys], t.Dict[str, t.Any], t.Dict[str, t.Any]]
    """
    A variable that contains the current user's data. Please see
    Please only use this with routes using the `@tornado.web.authenticated` decorator.
    """

    def get_current_user(
        self,
    ) -> t.Optional[
        t.Tuple[t.Optional[ApiKeys], t.Dict[str, t.Any], t.Dict[str, t.Any]]
    ]:
        """
        Get the token's API key, the token's payload and user data.

        Returns:
            t.Optional[ApiKeys]: The API key of the token.
            t.Dict[str, t.Any]: The token's payload.
            t.Dict[str, t.Any]: The user's data from the database.
        """
        return self.controller.authentication.check(self.get_cookie("token"))

    def autobleach(self, name, text):
        for r in self.redactables:
            if r in name:
                logger.debug(f"Auto-bleaching {name}: [**REDACTED**]")
                break
            logger.debug(f"Auto-bleaching {name}: {text}")
        if type(text) in self.nobleach:
            logger.debug("Auto-bleaching - bypass type")
            return text
        return bleach.clean(text)

    def get_argument(
        self,
        name: str,
        default: t.Union[
            None, str, tornado.web._ArgDefaultMarker
        ] = tornado.web._ARG_DEFAULT,
        strip: bool = True,
    ) -> t.Optional[str]:
        arg = self._get_argument(name, default, self.request.arguments, strip)
        return self.autobleach(name, arg)

    def get_arguments(self, name: str, strip: bool = True) -> t.List[str]:
        if not isinstance(strip, bool):
            raise AssertionError
        args = self._get_arguments(name, self.request.arguments, strip)
        args_ret = []
        for arg in args:
            args_ret += self.autobleach(name, arg)
        return args_ret

    def access_denied(self, user: t.Optional[str], reason: t.Optional[str]):
        ip = self.get_remote_ip()
        route = self.request.path
        if user is not None:
            user_data = f"User {user} from IP {ip}"
        else:
            user_data = f"An unknown user from IP {ip}"
        if reason:
            ending = f"to the API route {route} because {reason}"
        else:
            ending = f"to the API route {route}"
        logger.info(f"{user_data} was denied access {ending}")
        self.finish_json(
            403,
            {
                "status": "error",
                "error": "ACCESS_DENIED",
                "info": "You were denied access to the requested resource",
            },
        )

    def _auth_get_api_token(self) -> t.Optional[str]:
        """Get an API token from the request

        The API token is searched in the following order:
            1. The `token` query parameter
            2. The `Authorization` header
            3. The `token` cookie

        Returns:
            t.Optional[str]: The API token or None if no token was found.
        """
        logger.debug("Searching for specified token")
        api_token = self.get_query_argument("token", None)
        if api_token is None and self.request.headers.get("Authorization"):
            api_token = bearer_pattern.sub(
                "", self.request.headers.get("Authorization")
            )
        elif api_token is None:
            api_token = self.get_cookie("token")
        return api_token

    def authenticate_user(
        self,
    ) -> t.Optional[
        t.Tuple[
            t.List,
            t.List[EnumPermissionsCrafty],
            t.List[str],
            bool,
            t.Dict[str, t.Any],
        ]
    ]:
        try:
            api_key, _token_data, user = self.controller.authentication.check_err(
                self._auth_get_api_token()
            )

            superuser = user["superuser"]
            if api_key is not None:
                superuser = superuser and api_key.superuser

            exec_user_role = set()
            if superuser:
                authorized_servers = self.controller.servers.get_all_defined_servers()
                exec_user_role.add("Super User")
                exec_user_crafty_permissions = (
                    self.controller.crafty_perms.list_defined_crafty_permissions()
                )

            else:
                if api_key is not None:
                    exec_user_crafty_permissions = (
                        self.controller.crafty_perms.get_api_key_permissions_list(
                            api_key
                        )
                    )
                else:
                    exec_user_crafty_permissions = (
                        self.controller.crafty_perms.get_crafty_permissions_list(
                            user["user_id"]
                        )
                    )
                logger.debug(user["roles"])
                for r in user["roles"]:
                    role = self.controller.roles.get_role(r)
                    exec_user_role.add(role["role_name"])
                authorized_servers = self.controller.servers.get_authorized_servers(
                    user["user_id"]  # TODO: API key authorized servers?
                )
                authorized_servers = [
                    DatabaseShortcuts.get_data_obj(x.server_object)
                    for x in authorized_servers
                ]

            logger.debug("Checking results")
            if user:
                return (
                    authorized_servers,
                    exec_user_crafty_permissions,
                    exec_user_role,
                    superuser,
                    user,
                )
            logging.debug("Auth unsuccessful")
            self.access_denied(None, "the user provided an invalid token")
            return None
        except Exception as auth_exception:
            logger.debug(
                "An error occured while authenticating an API user:",
                exc_info=auth_exception,
            )
            self.finish_json(
                403,
                {
                    "status": "error",
                    "error": "ACCESS_DENIED",
                    "info": "An error occured while authenticating the user",
                },
            )
            return None

    def finish_json(self, status: int, data: t.Dict[str, t.Any]):
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(orjson.dumps(data))

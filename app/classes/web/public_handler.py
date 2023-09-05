import logging
import bleach

from app.classes.shared.helpers import Helpers
from app.classes.models.users import HelperUsers
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class PublicHandler(BaseHandler):
    def set_current_user(self, user_id: str = None):
        expire_days = self.helper.get_setting("cookie_expire")

        # if helper comes back with false
        if not expire_days:
            expire_days = "5"

        if user_id is not None:
            self.set_cookie(
                "token",
                self.controller.authentication.generate(user_id),
                expires_days=int(expire_days),
            )
        else:
            self.clear_cookie("token")
            # self.clear_cookie("user")
            # self.clear_cookie("user_data")

    def get(self, page=None):
        error = bleach.clean(self.get_argument("error", "Invalid Login!"))
        error_msg = bleach.clean(self.get_argument("error_msg", ""))

        page_data = {
            "version": self.helper.get_version_string(),
            "error": error,
            "lang": self.helper.get_setting("language"),
            "lang_page": self.helper.get_lang_page(self.helper.get_setting("language")),
            "query": "",
            "background": self.controller.cached_login,
            "login_opacity": self.controller.management.get_login_opacity(),
        }

        if self.request.query:
            page_data["query"] = self.request.query

        # sensible defaults
        template = "public/404.html"

        if page == "login":
            template = "public/login.html"

        elif page == "404":
            template = "public/404.html"

        elif page == "error":
            template = "public/error.html"

        elif page == "offline":
            template = "public/offline.html"

        elif page == "logout":
            self.clear_cookie("token")
            # self.clear_cookie("user")
            # self.clear_cookie("user_data")
            self.redirect("/login")
            return

        # if we have no page, let's go to login
        else:
            if self.request.query:
                self.redirect("/login?" + self.request.query)
            else:
                self.redirect("/login")
            return

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
            error_msg=error_msg,
        )

    def post(self, page=None):
        error = bleach.clean(self.get_argument("error", "Invalid Login!"))
        error_msg = bleach.clean(self.get_argument("error_msg", ""))

        page_data = {
            "version": self.helper.get_version_string(),
            "error": error,
            "lang": self.helper.get_setting("language"),
            "lang_page": self.helper.get_lang_page(self.helper.get_setting("language")),
            "query": "",
        }
        if self.request.query:
            page_data["query"] = self.request.query

        if page == "login":
            next_page = "/login"
            if self.request.query:
                next_page = "/login?" + self.request.query

            entered_username = bleach.clean(self.get_argument("username"))
            entered_password = bleach.clean(self.get_argument("password"))

            # pylint: disable=no-member
            try:
                user_id = HelperUsers.get_user_id_by_name(entered_username.lower())
                user_data = HelperUsers.get_user_model(user_id)
            except:
                error_msg = "Incorrect username or password. Please try again."
                # self.clear_cookie("user")
                # self.clear_cookie("user_data")
                self.clear_cookie("token")
                if self.request.query:
                    self.redirect(f"/login?error_msg={error_msg}&{self.request.query}")
                else:
                    self.redirect(f"/login?error_msg={error_msg}")
                return

            # if we don't have a user
            if not user_data:
                error_msg = "Incorrect username or password. Please try again."
                # self.clear_cookie("user")
                # self.clear_cookie("user_data")
                self.clear_cookie("token")
                if self.request.query:
                    self.redirect(f"/login?error_msg={error_msg}&{self.request.query}")
                else:
                    self.redirect(f"/login?error_msg={error_msg}")
                return

            # if they are disabled
            if not user_data.enabled:
                error_msg = (
                    "User account disabled. Please contact "
                    "your system administrator for more info."
                )
                # self.clear_cookie("user")
                # self.clear_cookie("user_data")
                self.clear_cookie("token")
                if self.request.query:
                    self.redirect(f"/login?error_msg={error_msg}&{self.request.query}")
                else:
                    self.redirect(f"/login?error_msg={error_msg}")
                return

            login_result = self.helper.verify_pass(entered_password, user_data.password)

            # Valid Login
            if login_result:
                self.set_current_user(user_data.user_id)
                logger.info(
                    f"User: {user_data} Logged in from IP: {self.get_remote_ip()}"
                )
                if not user_data.last_ip and user_data.username == "admin":
                    self.controller.first_login = True
                # record this login
                user_data.last_ip = self.get_remote_ip()
                user_data.last_login = Helpers.get_time_as_string()
                user_data.save()

                # log this login
                self.controller.management.add_to_audit_log(
                    user_data.user_id, "Logged in", 0, self.get_remote_ip()
                )

                if self.request.query_arguments.get("next"):
                    next_page = self.request.query_arguments.get("next")[0].decode()
                else:
                    next_page = "/panel/dashboard"

                self.redirect(next_page)
            else:
                # self.clear_cookie("user")
                # self.clear_cookie("user_data")
                self.clear_cookie("token")
                error_msg = "Incorrect username or password. Please try again."
                # log this failed login attempt
                self.controller.management.add_to_audit_log(
                    user_data.user_id, "Tried to log in", 0, self.get_remote_ip()
                )
                if self.request.query:
                    self.redirect(f"/login?error_msg={error_msg}&{self.request.query}")
                else:
                    self.redirect(f"/login?error_msg={error_msg}")
        else:
            if self.request.query:
                self.redirect("/login?" + self.request.query)
            else:
                self.redirect("/login")

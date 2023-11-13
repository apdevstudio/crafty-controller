import logging
from playhouse.shortcuts import model_to_dict

from app.classes.shared.helpers import Helpers  # pylint: disable=unused-import
from app.classes.shared.console import Console

logger = logging.getLogger(__name__)


class DatabaseBuilder:
    def __init__(self, database, helper, users_helper, management_helper):
        self.database = database
        self.helper = helper
        self.management_helper = management_helper
        self.users_helper = users_helper

    def default_settings(self, password="crafty"):
        logger.info("Fresh Install Detected - Creating Default Settings")
        Console.info("Fresh Install Detected - Creating Default Settings")
        default_data = self.helper.find_default_password()
        if not password in default_data:
            Console.help(
                "No default password found. Using password created "
                "by Crafty. Find it in app/config/default-creds.txt"
            )
        username = default_data.get("username", "admin")
        password = default_data.get("password", password)

        self.users_helper.add_user(
            username=username,
            password=password,
            email="default@example.com",
            superuser=True,
            manager=None,
        )

        self.management_helper.create_crafty_row()

    def is_fresh_install(self):
        try:
            num_user = self.users_helper.get_user_total()
            return num_user <= 0
        except:
            return True


class DatabaseShortcuts:
    # **********************************************************************************
    #                                  Generic Databse Methods
    # **********************************************************************************
    @staticmethod
    def return_rows(query):
        rows = []

        try:
            if query.count() > 0:
                for s in query:
                    rows.append(model_to_dict(s))
        except Exception as e:
            logger.warning(f"Database Error: {e}")

        return rows

    @staticmethod
    def return_db_rows(model):
        data = [model_to_dict(row) for row in model]
        return data

    @staticmethod
    def get_data_obj(obj):
        return model_to_dict(obj)

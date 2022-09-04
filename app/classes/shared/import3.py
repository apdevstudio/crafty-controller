import json
import os
import logging

from app.classes.controllers.users_controller import HelperUsers
from app.classes.shared.console import Console

logger = logging.getLogger(__name__)


class Import3:
    def __init__(self, helper, controller):
        self.helper = helper
        self.controller = controller

    def start_import(self):
        folder = os.path.normpath(
            input(
                "Please input the path to the migrations folder "
                "in your installation of Crafty 3: "
            )
        )
        if not os.path.exists(folder):
            Console.info(
                "Crafty cannot find the path you entered. "
                "Does Crafty's user have permission to access it?"
            )
            Console.info("Please run the import3 command again and enter a valid path.")
        else:
            with open(os.path.join(folder, "users.json"), encoding="utf-8") as f:
                user_json = json.loads(f.read())
            with open(os.path.join(folder, "mc_settings.json"), encoding="utf-8") as f:
                servers_json = json.loads(f.read())
            self.import_users(user_json)
            self.import_servers(servers_json, self.controller)

    def import_users(self, json_data):
        # If there is only one user to import json needs to call the data differently
        if isinstance(json_data, list):
            for user in json_data:
                if str(user["username"]).lower() != "admin":
                    HelperUsers.add_rawpass_user(
                        str(user["username"]).lower(), user["password"]
                    )
                    Console.info(f"Imported user {user['username']} from Crafty 3")
                    logger.info(f"Imported user {user['username']} from Crafty 3")
                else:
                    logger.info("Cannot create duplicate Admin account...skipping.")
        else:
            if str(json_data["username"]).lower() != "admin":
                HelperUsers.add_rawpass_user(
                    str(json_data["username"]).lower(), json_data["password"]
                )
                Console.info(f"Imported user {json_data['username']} from Crafty 3")
                logger.info(f"Imported user {json_data['username']} from Crafty 3")
            else:
                Console.info(
                    "There is only one user detected. "
                    "Cannot create duplicate Admin account."
                )
                logger.info(
                    "There is only one user detected. "
                    "Cannot create duplicate Admin account."
                )

    def import_servers(self, json_data, controller):
        # If there is only one server to import json needs to call the data differently
        if isinstance(json_data, list):
            for server in json_data:
                new_server_id = controller.import_jar_server(
                    server_name=server["server_name"],
                    server_path=server["server_path"],
                    server_jar=server["server_jar"],
                    min_mem=(int(server["memory_min"]) / 1000),
                    max_mem=(int(server["memory_max"]) / 1000),
                    port=server["server_port"],
                    user_id=HelperUsers.get_user_id_by_name("system"),
                )
                Console.info(
                    f"Imported server {server['server_name']}[{server['id']}] "
                    f"from Crafty 3 to new server id {new_server_id}"
                )
                logger.info(
                    f"Imported server {server['server_name']}[{server['id']}] "
                    f"from Crafty 3 to new server id {new_server_id}"
                )
        else:
            new_server_id = controller.import_jar_server(
                server_name=json_data["server_name"],
                server_path=json_data["server_path"],
                server_jar=json_data["server_jar"],
                min_mem=(int(json_data["memory_min"]) / 1000),
                max_mem=(int(json_data["memory_max"]) / 1000),
                port=json_data["server_port"],
                user_id=HelperUsers.get_user_id_by_name("system"),
            )
            Console.info(
                f"Imported server {json_data['server_name']}[{json_data['id']}] "
                f"from Crafty 3 to new server id {new_server_id}"
            )
            logger.info(
                f"Imported server {json_data['server_name']}[{json_data['id']}] "
                f"from Crafty 3 to new server id {new_server_id}"
            )

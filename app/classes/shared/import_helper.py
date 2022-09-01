import os
import time
import shutil
import logging
import threading
import urllib

from app.classes.controllers.server_perms_controller import PermissionsServers
from app.classes.controllers.servers_controller import ServersController
from app.classes.shared.helpers import Helpers
from app.classes.shared.file_helpers import FileHelpers

logger = logging.getLogger(__name__)


class ImportHelpers:
    allowed_quotes = ['"', "'", "`"]

    def __init__(self, helper, file_helper):
        self.file_helper: FileHelpers = file_helper
        self.helper: Helpers = helper

    def import_jar_server(self, server_path, new_server_dir, port, new_id):
        import_thread = threading.Thread(
            target=self.import_threaded_jar_server,
            daemon=True,
            args=(server_path, new_server_dir, port, new_id),
            name=f"{new_id}_import",
        )
        import_thread.start()

    def import_threaded_jar_server(self, server_path, new_server_dir, port, new_id):
        for item in os.listdir(server_path):
            if not item == "db_stats":
                try:
                    if os.path.isdir(os.path.join(server_path, item)):
                        FileHelpers.copy_dir(
                            os.path.join(server_path, item),
                            os.path.join(new_server_dir, item),
                        )
                    else:
                        FileHelpers.copy_file(
                            os.path.join(server_path, item),
                            os.path.join(new_server_dir, item),
                        )
                except shutil.Error as ex:
                    logger.error(f"Server import failed with error: {ex}")

        has_properties = False
        for item in os.listdir(new_server_dir):
            if str(item) == "server.properties":
                has_properties = True
        if not has_properties:
            logger.info(
                f"No server.properties found on zip file import. "
                f"Creating one with port selection of {str(port)}"
            )
            with open(
                os.path.join(new_server_dir, "server.properties"), "w", encoding="utf-8"
            ) as file:
                file.write(f"server-port={port}")
                file.close()
        time.sleep(5)
        ServersController.finish_import(new_id)
        server_users = PermissionsServers.get_server_user_list(new_id)
        for user in server_users:
            self.helper.websocket_helper.broadcast_user(user, "send_start_reload", {})

    def import_java_zip_server(self, temp_dir, new_server_dir, port, new_id):
        import_thread = threading.Thread(
            target=self.import_threaded_java_zip_server,
            daemon=True,
            args=(temp_dir, new_server_dir, port, new_id),
            name=f"{new_id}_java_zip_import",
        )
        import_thread.start()

    def import_threaded_java_zip_server(self, temp_dir, new_server_dir, port, new_id):
        has_properties = False
        # extracts archive to temp directory
        for item in os.listdir(temp_dir):
            if str(item) == "server.properties":
                has_properties = True
            try:
                if not os.path.isdir(os.path.join(temp_dir, item)):
                    FileHelpers.move_file(
                        os.path.join(temp_dir, item), os.path.join(new_server_dir, item)
                    )
                else:
                    if item != "db_stats":
                        FileHelpers.move_dir(
                            os.path.join(temp_dir, item),
                            os.path.join(new_server_dir, item),
                        )
            except Exception as ex:
                logger.error(f"ERROR IN ZIP IMPORT: {ex}")
        if not has_properties:
            logger.info(
                f"No server.properties found on zip file import. "
                f"Creating one with port selection of {str(port)}"
            )
            with open(
                os.path.join(new_server_dir, "server.properties"), "w", encoding="utf-8"
            ) as file:
                file.write(f"server-port={port}")
                file.close()

        server_users = PermissionsServers.get_server_user_list(new_id)
        ServersController.finish_import(new_id)
        for user in server_users:
            self.helper.websocket_helper.broadcast_user(user, "send_start_reload", {})
        # deletes temp dir
        FileHelpers.del_dirs(temp_dir)

    def import_bedrock_server(
        self, server_path, new_server_dir, port, full_jar_path, new_id
    ):
        import_thread = threading.Thread(
            target=self.import_threaded_bedrock_server,
            daemon=True,
            args=(server_path, new_server_dir, port, full_jar_path, new_id),
            name=f"{new_id}_bedrock_import",
        )
        import_thread.start()

    def import_threaded_bedrock_server(
        self, server_path, new_server_dir, port, full_jar_path, new_id
    ):
        for item in os.listdir(server_path):
            if not item == "db_stats":
                try:
                    if os.path.isdir(os.path.join(server_path, item)):
                        FileHelpers.copy_dir(
                            os.path.join(server_path, item),
                            os.path.join(new_server_dir, item),
                        )
                    else:
                        FileHelpers.copy_file(
                            os.path.join(server_path, item),
                            os.path.join(new_server_dir, item),
                        )
                except shutil.Error as ex:
                    logger.error(f"Server import failed with error: {ex}")

        has_properties = False
        for item in os.listdir(new_server_dir):
            if str(item) == "server.properties":
                has_properties = True
        if not has_properties:
            logger.info(
                f"No server.properties found on zip file import. "
                f"Creating one with port selection of {str(port)}"
            )
            with open(
                os.path.join(new_server_dir, "server.properties"), "w", encoding="utf-8"
            ) as file:
                file.write(f"server-port={port}")
                file.close()
        if os.name != "nt":
            if Helpers.check_file_exists(full_jar_path):
                os.chmod(full_jar_path, 0o2760)
        ServersController.finish_import(new_id)
        server_users = PermissionsServers.get_server_user_list(new_id)
        for user in server_users:
            self.helper.websocket_helper.broadcast_user(user, "send_start_reload", {})

    def import_bedrock_zip_server(
        self, temp_dir, new_server_dir, full_jar_path, port, new_id
    ):
        import_thread = threading.Thread(
            target=self.import_threaded_bedrock_zip_server,
            daemon=True,
            args=(temp_dir, new_server_dir, full_jar_path, port, new_id),
            name=f"{new_id}_bedrock_import",
        )
        import_thread.start()

    def import_threaded_bedrock_zip_server(
        self, temp_dir, new_server_dir, full_jar_path, port, new_id
    ):
        has_properties = False
        # extracts archive to temp directory
        for item in os.listdir(temp_dir):
            if str(item) == "server.properties":
                has_properties = True
            try:
                if not os.path.isdir(os.path.join(temp_dir, item)):
                    FileHelpers.move_file(
                        os.path.join(temp_dir, item), os.path.join(new_server_dir, item)
                    )
                else:
                    if item != "db_stats":
                        FileHelpers.move_dir(
                            os.path.join(temp_dir, item),
                            os.path.join(new_server_dir, item),
                        )
            except Exception as ex:
                logger.error(f"ERROR IN ZIP IMPORT: {ex}")
        if not has_properties:
            logger.info(
                f"No server.properties found on zip file import. "
                f"Creating one with port selection of {str(port)}"
            )
            with open(
                os.path.join(new_server_dir, "server.properties"), "w", encoding="utf-8"
            ) as file:
                file.write(f"server-port={port}")
                file.close()
        ServersController.finish_import(new_id)
        server_users = PermissionsServers.get_server_user_list(new_id)
        for user in server_users:
            self.helper.websocket_helper.broadcast_user(user, "send_start_reload", {})
        if os.name != "nt":
            if Helpers.check_file_exists(full_jar_path):
                os.chmod(full_jar_path, 0o2760)
        # deletes temp dir
        FileHelpers.del_dirs(temp_dir)

    def download_bedrock_server(self, path, new_id):
        download_thread = threading.Thread(
            target=self.download_threaded_bedrock_server,
            daemon=True,
            args=(path, new_id),
            name=f"{new_id}_download",
        )
        download_thread.start()

    def download_threaded_bedrock_server(self, path, new_id):

        # downloads zip from remote url
        try:
            bedrock_url = Helpers.get_latest_bedrock_url()
            if bedrock_url.lower().startswith("https"):
                urllib.request.urlretrieve(
                    bedrock_url,
                    os.path.join(path, "bedrock_server.zip"),
                )

            unzip_path = os.path.join(path, "bedrock_server.zip")
            unzip_path = self.helper.wtol_path(unzip_path)
            # unzips archive that was downloaded.
            FileHelpers.unzip_file(unzip_path)
            # adjusts permissions for execution if os is not windows
            if not self.helper.is_os_windows():
                os.chmod(os.path.join(path, "bedrock_server"), 0o0744)

            # we'll delete the zip we downloaded now
            os.remove(os.path.join(path, "bedrock_server.zip"))
        except Exception as e:
            logger.critical(f"Failed to download bedrock executable for update \n{e}")

        ServersController.finish_import(new_id)
        server_users = PermissionsServers.get_server_user_list(new_id)
        for user in server_users:
            self.helper.websocket_helper.broadcast_user(user, "send_start_reload", {})

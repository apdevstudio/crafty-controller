import os
import shutil
import logging
import pathlib
import tempfile
import zipfile
from zipfile import ZipFile, ZIP_DEFLATED

from app.classes.shared.helpers import Helpers
from app.classes.shared.console import Console
from app.classes.shared.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class FileHelpers:
    allowed_quotes = ['"', "'", "`"]

    def __init__(self, helper):
        self.helper: Helpers = helper

    @staticmethod
    def del_dirs(path):
        path = pathlib.Path(path)
        for sub in path.iterdir():
            if sub.is_dir():
                # Delete folder if it is a folder
                FileHelpers.del_dirs(sub)
            else:
                # Delete file if it is a file:
                try:
                    sub.unlink()
                except:
                    logger.error(f"Unable to delete file {sub}")
        try:
            # This removes the top-level folder:
            path.rmdir()
        except:
            logger.error("Unable to remove top level")
        return True

    @staticmethod
    def del_file(path):
        path = pathlib.Path(path)
        try:
            logger.debug(f"Deleting file: {path}")
            # Remove the file
            os.remove(path)
            return True
        except FileNotFoundError:
            logger.error(f"Path specified is not a file or does not exist. {path}")
            return False

    @staticmethod
    def copy_dir(src_path, dest_path, dirs_exist_ok=False):
        # pylint: disable=unexpected-keyword-arg
        shutil.copytree(src_path, dest_path, dirs_exist_ok=dirs_exist_ok)

    @staticmethod
    def copy_file(src_path, dest_path):
        shutil.copy(src_path, dest_path)

    @staticmethod
    def move_dir(src_path, dest_path):
        FileHelpers.copy_dir(src_path, dest_path)
        FileHelpers.del_dirs(src_path)

    @staticmethod
    def move_dir_exist(src_path, dest_path):
        FileHelpers.copy_dir(src_path, dest_path, True)
        FileHelpers.del_dirs(src_path)

    @staticmethod
    def move_file(src_path, dest_path):
        FileHelpers.copy_file(src_path, dest_path)
        FileHelpers.del_file(src_path)

    @staticmethod
    def make_archive(path_to_destination, path_to_zip, comment=""):
        # create a ZipFile object
        path_to_destination += ".zip"
        with ZipFile(path_to_destination, "w") as zip_file:
            zip_file.comment = bytes(
                comment, "utf-8"
            )  # comments over 65535 bytes will be truncated
            for root, _dirs, files in os.walk(path_to_zip, topdown=True):
                ziproot = path_to_zip
                for file in files:
                    try:
                        logger.info(f"backing up: {os.path.join(root, file)}")
                        if os.name == "nt":
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, ""), file),
                            )
                        else:
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, "/"), file),
                            )

                    except Exception as e:
                        logger.warning(
                            f"Error backing up: {os.path.join(root, file)}!"
                            f" - Error was: {e}"
                        )
        return True

    @staticmethod
    def make_compressed_archive(path_to_destination, path_to_zip, comment=""):
        # create a ZipFile object
        path_to_destination += ".zip"
        with ZipFile(path_to_destination, "w", ZIP_DEFLATED) as zip_file:
            zip_file.comment = bytes(
                comment, "utf-8"
            )  # comments over 65535 bytes will be truncated
            for root, _dirs, files in os.walk(path_to_zip, topdown=True):
                ziproot = path_to_zip
                for file in files:
                    try:
                        logger.info(f"packaging: {os.path.join(root, file)}")
                        if os.name == "nt":
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, ""), file),
                            )
                        else:
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, "/"), file),
                            )

                    except Exception as e:
                        logger.warning(
                            f"Error packaging: {os.path.join(root, file)}!"
                            f" - Error was: {e}"
                        )

        return True

    def make_compressed_backup(
        self, path_to_destination, path_to_zip, excluded_dirs, server_id, comment=""
    ):
        # create a ZipFile object
        path_to_destination += ".zip"
        ex_replace = [p.replace("\\", "/") for p in excluded_dirs]
        total_bytes = 0
        dir_bytes = Helpers.get_dir_size(path_to_zip)
        results = {
            "percent": 0,
            "total_files": self.helper.human_readable_file_size(dir_bytes),
        }
        WebSocketManager().broadcast_page_params(
            "/panel/server_detail",
            {"id": str(server_id)},
            "backup_status",
            results,
        )
        with ZipFile(path_to_destination, "w", ZIP_DEFLATED) as zip_file:
            zip_file.comment = bytes(
                comment, "utf-8"
            )  # comments over 65535 bytes will be truncated
            for root, dirs, files in os.walk(path_to_zip, topdown=True):
                for l_dir in dirs:
                    if str(os.path.join(root, l_dir)).replace("\\", "/") in ex_replace:
                        dirs.remove(l_dir)
                ziproot = path_to_zip
                for file in files:
                    if (
                        str(os.path.join(root, file)).replace("\\", "/")
                        not in ex_replace
                        and file != "crafty.sqlite"
                    ):
                        try:
                            logger.info(f"backing up: {os.path.join(root, file)}")
                            if os.name == "nt":
                                zip_file.write(
                                    os.path.join(root, file),
                                    os.path.join(root.replace(ziproot, ""), file),
                                )
                            else:
                                zip_file.write(
                                    os.path.join(root, file),
                                    os.path.join(root.replace(ziproot, "/"), file),
                                )

                        except Exception as e:
                            logger.warning(
                                f"Error backing up: {os.path.join(root, file)}!"
                                f" - Error was: {e}"
                            )
                    total_bytes += os.path.getsize(os.path.join(root, file))
                    percent = round((total_bytes / dir_bytes) * 100, 2)
                    results = {
                        "percent": percent,
                        "total_files": self.helper.human_readable_file_size(dir_bytes),
                    }
                    WebSocketManager().broadcast_page_params(
                        "/panel/server_detail",
                        {"id": str(server_id)},
                        "backup_status",
                        results,
                    )

        return True

    def make_backup(
        self, path_to_destination, path_to_zip, excluded_dirs, server_id, comment=""
    ):
        # create a ZipFile object
        path_to_destination += ".zip"
        ex_replace = [p.replace("\\", "/") for p in excluded_dirs]
        total_bytes = 0
        dir_bytes = Helpers.get_dir_size(path_to_zip)
        results = {
            "percent": 0,
            "total_files": self.helper.human_readable_file_size(dir_bytes),
        }
        WebSocketManager().broadcast_page_params(
            "/panel/server_detail",
            {"id": str(server_id)},
            "backup_status",
            results,
        )
        with ZipFile(path_to_destination, "w") as zip_file:
            zip_file.comment = bytes(
                comment, "utf-8"
            )  # comments over 65535 bytes will be truncated
            for root, dirs, files in os.walk(path_to_zip, topdown=True):
                for l_dir in dirs[:]:
                    # make all paths in exclusions a unix style slash
                    # to match directories.
                    if str(os.path.join(root, l_dir)).replace("\\", "/") in ex_replace:
                        dirs.remove(l_dir)
                ziproot = path_to_zip
                # iterate through list of files
                for file in files:
                    # check if file/dir is in exclusions list.
                    # Only proceed if not exluded.
                    if (
                        str(os.path.join(root, file)).replace("\\", "/")
                        not in ex_replace
                        and file != "crafty.sqlite"
                    ):
                        try:
                            logger.debug(f"backing up: {os.path.join(root, file)}")
                            # add trailing slash to zip root dir if not windows.
                            if os.name == "nt":
                                zip_file.write(
                                    os.path.join(root, file),
                                    os.path.join(root.replace(ziproot, ""), file),
                                )
                            else:
                                zip_file.write(
                                    os.path.join(root, file),
                                    os.path.join(root.replace(ziproot, "/"), file),
                                )

                        except Exception as e:
                            logger.warning(
                                f"Error backing up: {os.path.join(root, file)}!"
                                f" - Error was: {e}"
                            )
                    # debug logging for exlusions list
                    else:
                        logger.debug(f"Found {file} in exclusion list. Skipping...")

                    # add current file bytes to total bytes.
                    total_bytes += os.path.getsize(os.path.join(root, file))
                    # calcualte percentage based off total size and current archive size
                    percent = round((total_bytes / dir_bytes) * 100, 2)
                    # package results
                    results = {
                        "percent": percent,
                        "total_files": self.helper.human_readable_file_size(dir_bytes),
                    }
                    # send status results to page.
                    WebSocketManager().broadcast_page_params(
                        "/panel/server_detail",
                        {"id": str(server_id)},
                        "backup_status",
                        results,
                    )
        return True

    @staticmethod
    def unzip_file(zip_path, server_update=False):
        ignored_names = ["server.properties", "permissions.json", "allowlist.json"]
        # Get directory without zipfile name
        new_dir = pathlib.Path(zip_path).parents[0]
        # make sure we're able to access the zip file
        if Helpers.check_file_perms(zip_path) and os.path.isfile(zip_path):
            # make sure the directory we're unzipping this to exists
            Helpers.ensure_dir_exists(new_dir)
            # we'll make a temporary directory to unzip this to.
            temp_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    # we'll extract this to the temp dir using zipfile module
                    zip_ref.extractall(temp_dir)
                # we'll iterate through the top level directory moving everything
                # out of the temp directory and into it's final home.
                for item in os.listdir(temp_dir):
                    # if the file is one of our ignored names we'll skip it
                    if item in ignored_names and server_update:
                        continue
                    # we handle files and dirs differently or we'll crash out.
                    if os.path.isdir(os.path.join(temp_dir, item)):
                        try:
                            FileHelpers.move_dir_exist(
                                os.path.join(temp_dir, item),
                                os.path.join(new_dir, item),
                            )
                        except Exception as ex:
                            logger.error(f"ERROR IN ZIP IMPORT: {ex}")
                    else:
                        try:
                            FileHelpers.move_file(
                                os.path.join(temp_dir, item),
                                os.path.join(new_dir, item),
                            )
                        except Exception as ex:
                            logger.error(f"ERROR IN ZIP IMPORT: {ex}")
            except Exception as ex:
                Console.error(ex)
        else:
            return "false"
        return

    # TODO Look if not redundant with the precendent function
    # TODO Prefixed ajax_ to differentiate and not broke things

    def ajax_unzip_server(self, zip_path, user_id):
        if Helpers.check_file_perms(zip_path):
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # extracts archive to temp directory
                zip_ref.extractall(temp_dir)
            if user_id:
                WebSocketManager().broadcast_user(
                    user_id, "send_temp_path", {"path": temp_dir}
                )

    def ajax_backup_select(self, path, user_id):
        if user_id:
            WebSocketManager().broadcast_user(user_id, "send_temp_path", {"path": path})

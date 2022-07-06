import os
import shutil
import logging
import pathlib
import tempfile
import zipfile
from zipfile import ZipFile, ZIP_DEFLATED

from app.classes.shared.helpers import Helpers
from app.classes.shared.console import Console

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
                sub.unlink()

        # This removes the top-level folder:
        path.rmdir()
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
    def move_file(src_path, dest_path):
        FileHelpers.copy_file(src_path, dest_path)
        FileHelpers.del_file(src_path)

    @staticmethod
    def make_archive(path_to_destination, path_to_zip):
        # create a ZipFile object
        path_to_destination += ".zip"
        with ZipFile(path_to_destination, "w") as zip_file:
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
    def make_compressed_archive(path_to_destination, path_to_zip):
        # create a ZipFile object
        path_to_destination += ".zip"
        with ZipFile(path_to_destination, "w", ZIP_DEFLATED) as zip_file:
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
        self, path_to_destination, path_to_zip, excluded_dirs, server_id
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
        self.helper.websocket_helper.broadcast_page_params(
            "/panel/server_detail",
            {"id": str(server_id)},
            "backup_status",
            results,
        )
        with ZipFile(path_to_destination, "w", ZIP_DEFLATED) as zip_file:
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
                    self.helper.websocket_helper.broadcast_page_params(
                        "/panel/server_detail",
                        {"id": str(server_id)},
                        "backup_status",
                        results,
                    )

        return True

    def make_backup(self, path_to_destination, path_to_zip, excluded_dirs, server_id):
        # create a ZipFile object
        path_to_destination += ".zip"
        ex_replace = [p.replace("\\", "/") for p in excluded_dirs]
        total_bytes = 0
        dir_bytes = Helpers.get_dir_size(path_to_zip)
        results = {
            "percent": 0,
            "total_files": self.helper.human_readable_file_size(dir_bytes),
        }
        self.helper.websocket_helper.broadcast_page_params(
            "/panel/server_detail",
            {"id": str(server_id)},
            "backup_status",
            results,
        )
        with ZipFile(path_to_destination, "w") as zip_file:
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
                    self.helper.websocket_helper.broadcast_page_params(
                        "/panel/server_detail",
                        {"id": str(server_id)},
                        "backup_status",
                        results,
                    )
        return True

    @staticmethod
    def unzip_file(zip_path):
        new_dir_list = zip_path.split("/")
        new_dir = ""
        for i in range(len(new_dir_list) - 1):
            if i == 0:
                new_dir += new_dir_list[i]
            else:
                new_dir += "/" + new_dir_list[i]

        if Helpers.check_file_perms(zip_path) and os.path.isfile(zip_path):
            Helpers.ensure_dir_exists(new_dir)
            temp_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                for i in enumerate(zip_ref.filelist):
                    if len(zip_ref.filelist) > 1 or not zip_ref.filelist[
                        i
                    ].filename.endswith("/"):
                        break

                full_root_path = temp_dir

                for item in os.listdir(full_root_path):
                    if os.path.isdir(os.path.join(full_root_path, item)):
                        try:
                            FileHelpers.move_dir(
                                os.path.join(full_root_path, item),
                                os.path.join(new_dir, item),
                            )
                        except Exception as ex:
                            logger.error(f"ERROR IN ZIP IMPORT: {ex}")
                    else:
                        try:
                            FileHelpers.move_file(
                                os.path.join(full_root_path, item),
                                os.path.join(new_dir, item),
                            )
                        except Exception as ex:
                            logger.error(f"ERROR IN ZIP IMPORT: {ex}")
            except Exception as ex:
                Console.error(ex)
        else:
            return "false"
        return

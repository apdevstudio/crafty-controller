import contextlib
import os
import re
import sys
import json
import tempfile
import time
import uuid
import string
import base64
import socket
import secrets
import logging
import html
import zipfile
import pathlib
import ctypes
import subprocess
import itertools
from datetime import datetime
from socket import gethostname
from contextlib import redirect_stderr, suppress
import libgravatar
from packaging import version as pkg_version

from app.classes.shared.null_writer import NullWriter
from app.classes.shared.console import Console
from app.classes.shared.installer import installer
from app.classes.shared.translation import Translation
from app.classes.web.websocket_helper import WebSocketHelper

with redirect_stderr(NullWriter()):
    import psutil

# winreg is only a package on windows-python. We will only import
# this on windows systems to avoid a module not found error
# this is only needed for windows java path shenanigans
if os.name == "nt":
    import winreg

logger = logging.getLogger(__name__)

try:
    import requests
    from requests import get
    from OpenSSL import crypto
    from argon2 import PasswordHasher

except ModuleNotFoundError as err:
    logger.critical(f"Import Error: Unable to load {err.name} module", exc_info=True)
    print(f"Import Error: Unable to load {err.name} module")
    installer.do_install()


class Helpers:
    allowed_quotes = ['"', "'", "`"]

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.curdir)
        self.config_dir = os.path.join(self.root_dir, "app", "config")
        self.webroot = os.path.join(self.root_dir, "app", "frontend")
        self.servers_dir = os.path.join(self.root_dir, "servers")
        self.backup_path = os.path.join(self.root_dir, "backups")
        self.migration_dir = os.path.join(self.root_dir, "app", "migrations")

        self.session_file = os.path.join(self.root_dir, "app", "config", "session.lock")
        self.settings_file = os.path.join(self.root_dir, "app", "config", "config.json")

        self.ensure_dir_exists(os.path.join(self.root_dir, "app", "config", "db"))
        self.db_path = os.path.join(
            self.root_dir, "app", "config", "db", "crafty.sqlite"
        )
        self.serverjar_cache = os.path.join(self.config_dir, "serverjars.json")
        self.credits_cache = os.path.join(self.config_dir, "credits.json")
        self.passhasher = PasswordHasher()
        self.exiting = False

        self.websocket_helper = WebSocketHelper(self)
        self.translation = Translation(self)
        self.update_available = False

    @staticmethod
    def auto_installer_fix(ex):
        logger.critical(f"Import Error: Unable to load {ex.name} module", exc_info=True)
        print(f"Import Error: Unable to load {ex.name} module")
        installer.do_install()

    def check_remote_version(self):
        """
        Check if the remote version is newer than the local version
        Returning remote version if it is newer, otherwise False.
        """
        try:
            # Get tags from Gitlab, select the latest and parse the semver
            response = get(
                "https://gitlab.com/api/v4/projects/20430749/repository/tags"
            )
            if response.status_code == 200:
                remote_version = pkg_version.parse(json.loads(response.text)[0]["name"])

            # Get local version data from the file and parse the semver
            local_version = pkg_version.parse(self.get_version_string())

            if remote_version > local_version:
                return remote_version

        except Exception as e:
            logger.error(f"Unable to check for new crafty version! \n{e}")
        return False

    @staticmethod
    def get_latest_bedrock_url():
        """
        Get latest bedrock executable url \n\n
        returns url if successful, False if not
        """
        url = "https://minecraft.net/en-us/download/server/bedrock/"
        headers = {
            "Accept-Encoding": "identity",
            "Accept-Language": "en",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/104.0.0.0 Safari/537.36"
            ),
        }
        target_win = 'https://minecraft.azureedge.net/bin-win/[^"]*'
        target_linux = 'https://minecraft.azureedge.net/bin-linux/[^"]*'

        try:
            # Get minecraft server download page
            # (hopefully the don't change the structure)
            download_page = get(url, headers=headers)

            # Search for our string targets
            win_download_url = re.search(target_win, download_page.text).group(0)
            linux_download_url = re.search(target_linux, download_page.text).group(0)

            if os.name == "nt":
                return win_download_url

            return linux_download_url
        except Exception as e:
            logger.error(f"Unable to resolve remote bedrock download url! \n{e}")
        return False

    @staticmethod
    def find_java_installs():
        # If we're windows return oracle java versions,
        # otherwise java vers need to be manual.
        if os.name == "nt":
            # Adapted from LeeKamentsky >>>
            # https://github.com/LeeKamentsky/python-javabridge/blob/master/javabridge/locate.py
            jdk_key_paths = (
                "SOFTWARE\\JavaSoft\\JDK",
                "SOFTWARE\\JavaSoft\\Java Development Kit",
            )
            java_paths = []
            for jdk_key_path in jdk_key_paths:
                try:
                    with suppress(OSError), winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, jdk_key_path
                    ) as kjdk:
                        for i in itertools.count():
                            version = winreg.EnumKey(kjdk, i)
                            kjdk_current = winreg.OpenKey(
                                winreg.HKEY_LOCAL_MACHINE,
                                jdk_key_path,
                            )
                            kjdk_current = winreg.OpenKey(
                                winreg.HKEY_LOCAL_MACHINE,
                                jdk_key_path + "\\" + version,
                            )
                            kjdk_current_values = dict(  # pylint: disable=consider-using-dict-comprehension
                                [
                                    winreg.EnumValue(kjdk_current, i)[:2]
                                    for i in range(winreg.QueryInfoKey(kjdk_current)[1])
                                ]
                            )
                            java_paths.append(kjdk_current_values["JavaHome"])
                except OSError as e:
                    if e.errno == 2:
                        continue
                    raise
            return java_paths

        # If we get here we're linux so we will use 'update-alternatives'
        # (If distro does not have update-alternatives then manual input.)

        # Sometimes u-a will be in /sbin on some distros (which is annoying.)
        ua_path = "/usr/bin/update-alternatives"
        if not os.path.exists(ua_path):
            logger.warning("update-alternatives not found! Trying /sbin")
            ua_path = "/usr/sbin/update-alternatives"

        try:
            paths = subprocess.check_output(
                [ua_path, "--list", "java"], encoding="utf8"
            )

            if re.match("^(/[^/ ]*)+/?$", paths):
                return paths.split("\n")

        except Exception as e:
            logger.error(f"Java Detect Error: {e}")
            return []

    @staticmethod
    def float_to_string(gbs: float):
        s = str(float(gbs) * 1000).rstrip("0").rstrip(".")
        return s

    @staticmethod
    def check_file_perms(path):
        try:
            with open(path, "r", encoding="utf-8"):
                pass
            logger.info(f"{path} is readable")
            return True
        except PermissionError:
            return False

    @staticmethod
    def is_file_older_than_x_days(file, days=1):
        if Helpers.check_file_exists(file):
            file_time = os.path.getmtime(file)
            # Check against 24 hours
            return (time.time() - file_time) / 3600 > 24 * days
        logger.error(f"{file} does not exist")
        return True

    def get_servers_root_dir(self):
        return self.servers_dir

    @staticmethod
    def which_java():
        # Adapted from LeeKamentsky >>>
        # https://github.com/LeeKamentsky/python-javabridge/blob/master/javabridge/locate.py
        jdk_key_paths = (
            "SOFTWARE\\JavaSoft\\JDK",
            "SOFTWARE\\JavaSoft\\Java Development Kit",
        )
        for jdk_key_path in jdk_key_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, jdk_key_path) as kjdk:
                    kjdk_values = (
                        dict(  # pylint: disable=consider-using-dict-comprehension
                            [
                                winreg.EnumValue(kjdk, i)[:2]
                                for i in range(winreg.QueryInfoKey(kjdk)[1])
                            ]
                        )
                    )
                    current_version = kjdk_values["CurrentVersion"]
                    kjdk_current = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, jdk_key_path + "\\" + current_version
                    )
                    kjdk_current_values = (
                        dict(  # pylint: disable=consider-using-dict-comprehension
                            [
                                winreg.EnumValue(kjdk_current, i)[:2]
                                for i in range(winreg.QueryInfoKey(kjdk_current)[1])
                            ]
                        )
                    )
                    return kjdk_current_values["JavaHome"]
            except OSError as e:
                if e.errno == 2:
                    continue
                raise

    @staticmethod
    def check_internet():
        try:
            requests.get("https://google.com", timeout=1)
            return True
        except Exception:
            return False

    @staticmethod
    def check_port(server_port):
        try:
            ip = get("https://api.ipify.org").content.decode("utf8")
        except:
            ip = "google.com"
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a_socket.settimeout(20.0)

        location = (ip, server_port)
        result_of_check = a_socket.connect_ex(location)

        a_socket.close()

        return result_of_check == 0

    @staticmethod
    def check_server_conn(server_port):
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a_socket.settimeout(10.0)
        ip = "127.0.0.1"

        location = (ip, server_port)
        result_of_check = a_socket.connect_ex(location)
        a_socket.close()

        return result_of_check == 0

    @staticmethod
    def cmdparse(cmd_in):
        # Parse a string into arguments
        cmd_out = []  # "argv" output array
        cmd_index = (
            -1
        )  # command index - pointer to the argument we're building in cmd_out
        new_param = True  # whether we're creating a new argument/parameter
        esc = False  # whether an escape character was encountered
        quote_char = None  # if we're dealing with a quote, save the quote type here.
        # Nested quotes to be dealt with by the command
        for char in cmd_in:  # for character in string
            if (
                new_param
            ):  # if set, begin a new argument and increment the command index.
                # Continue the loop.
                if char == " ":
                    continue
                cmd_index += 1
                cmd_out.append("")
                new_param = False
            if esc:  # if we encountered an escape character on the last loop,
                # append this char regardless of what it is
                if char not in Helpers.allowed_quotes:
                    cmd_out[cmd_index] += "\\"
                cmd_out[cmd_index] += char
                esc = False
            else:
                if char == "\\":  # if the current character is an escape character,
                    # set the esc flag and continue to next loop
                    esc = True
                elif (
                    char == " " and quote_char is None
                ):  # if we encounter a space and are not dealing with a quote,
                    # set the new argument flag and continue to next loop
                    new_param = True
                elif (
                    char == quote_char
                ):  # if we encounter the character that matches our start quote,
                    # end the quote and continue to next loop
                    quote_char = None
                elif quote_char is None and (
                    char in Helpers.allowed_quotes
                ):  # if we're not in the middle of a quote and we get a quotable
                    # character, start a quote and proceed to the next loop
                    quote_char = char
                else:  # else, just store the character in the current arg
                    cmd_out[cmd_index] += char
        return cmd_out

    def get_setting(self, key, default_return=False):
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if key in data.keys():
                return data.get(key)

            logger.error(f'Config File Error: Setting "{key}" does not exist')
            Console.error(f'Config File Error: Setting "{key}" does not exist')

        except Exception as e:
            logger.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )
            Console.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )

        return default_return

    def set_settings(self, data):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            logger.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )
            Console.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )
            return False

        return True

    @staticmethod
    def get_master_config():
        # Make changes for users' local config.json files here. As of 4.0.20
        # Config.json was removed from the repo to make it easier for users
        # To make non-breaking changes to the file.
        return {
            "http_port": 8000,
            "https_port": 8443,
            "language": "en_EN",
            "cookie_expire": 30,
            "cookie_secret": "random",
            "apikey_secret": "random",
            "show_errors": True,
            "history_max_age": 7,
            "stats_update_frequency": 30,
            "delete_default_json": False,
            "show_contribute_link": True,
            "virtual_terminal_lines": 70,
            "max_log_lines": 700,
            "max_audit_entries": 300,
            "disabled_language_files": ["lol_EN.json", ""],
            "stream_size_GB": 1,
            "keywords": ["help", "chunk"],
            "allow_nsfw_profile_pictures": False,
            "enable_user_self_delete": False,
        }

    def get_all_settings(self):
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:
            data = {}
            logger.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )
            Console.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )

        return data

    @staticmethod
    def is_subdir(server_path, root_dir):
        server_path = os.path.realpath(server_path)
        root_dir = os.path.realpath(root_dir)

        relative = os.path.relpath(server_path, root_dir)

        if relative.startswith(os.pardir):
            return False
        return True

    def set_setting(self, key, new_value):
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if key in data.keys():
                data[key] = new_value
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return True

            logger.error(f'Config File Error: Setting "{key}" does not exist')
            Console.error(f'Config File Error: Setting "{key}" does not exist')

        except Exception as e:
            logger.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )
            Console.critical(
                f"Config File Error: Unable to read {self.settings_file} due to {e}"
            )
        return False

    @staticmethod
    def get_themes():
        return ["default", "dark", "light", "ronald"]

    @staticmethod
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_version(self):
        version_data = {}
        try:
            with open(
                os.path.join(self.config_dir, "version.json"), "r", encoding="utf-8"
            ) as f:
                version_data = json.load(f)

        except Exception as e:
            Console.critical(f"Unable to get version data! \n{e}")

        return version_data

    @staticmethod
    def get_announcements():
        data = (
            '[{"id":"1","date":"Unknown",'
            '"title":"Error getting Announcements",'
            '"desc":"Error getting Announcements","link":""}]'
        )

        try:
            response = requests.get("https://craftycontrol.com/notify.json", timeout=2)
            data = json.loads(response.content)
        except Exception as e:
            logger.error(f"Failed to fetch notifications with error: {e}")

        return data

    def get_version_string(self):
        version_data = self.get_version()
        major = version_data.get("major", "?")
        minor = version_data.get("minor", "?")
        sub = version_data.get("sub", "?")

        # set some defaults if we don't get version_data from our helper
        version = f"{major}.{minor}.{sub}"
        return str(version)

    def encode_pass(self, password):
        return self.passhasher.hash(password)

    def verify_pass(self, password, currenthash):
        try:
            self.passhasher.verify(currenthash, password)
            return True
        except:
            return False

    def log_colors(self, line):
        # our regex replacements
        # note these are in a tuple

        user_keywords = self.get_setting("keywords")

        replacements = [
            (r"(\[.+?/INFO\])", r'<span class="mc-log-info">\1</span>'),
            (r"(\[.+?/WARN\])", r'<span class="mc-log-warn">\1</span>'),
            (r"(\[.+?/ERROR\])", r'<span class="mc-log-error">\1</span>'),
            (r"(\[.+?/FATAL\])", r'<span class="mc-log-fatal">\1</span>'),
            (
                r"(\w+?\[/\d+?\.\d+?\.\d+?\.\d+?\:\d+?\])",
                r'<span class="mc-log-keyword">\1</span>',
            ),
            (r"\[(\d\d:\d\d:\d\d)\]", r'<span class="mc-log-time">[\1]</span>'),
            (r"(\[.+? INFO\])", r'<span class="mc-log-info">\1</span>'),
            (r"(\[.+? WARN\])", r'<span class="mc-log-warn">\1</span>'),
            (r"(\[.+? ERROR\])", r'<span class="mc-log-error">\1</span>'),
            (r"(\[.+? FATAL\])", r'<span class="mc-log-fatal">\1</span>'),
        ]

        # highlight users keywords
        for keyword in user_keywords:
            # pylint: disable=consider-using-f-string
            search_replace = (
                r"({})".format(keyword),
                r'<span class="mc-log-keyword">\1</span>',
            )
            replacements.append(search_replace)

        for old, new in replacements:
            line = re.sub(old, new, line, flags=re.IGNORECASE)

        return line

    @staticmethod
    def validate_traversal(base_path, filename):
        logger.debug(f'Validating traversal ("{base_path}", "{filename}")')
        base = pathlib.Path(base_path).resolve()
        file = pathlib.Path(filename)
        fileabs = base.joinpath(file).resolve()
        common_path = pathlib.Path(os.path.commonpath([base, fileabs]))
        if base == common_path:
            return fileabs
        raise ValueError("Path traversal detected")

    @staticmethod
    def tail_file(file_name, number_lines=20):
        if not Helpers.check_file_exists(file_name):
            logger.warning(f"Unable to find file to tail: {file_name}")
            return [f"Unable to find file to tail: {file_name}"]

        # length of lines is X char here
        avg_line_length = 255

        # create our buffer number - number of lines * avg_line_length
        line_buffer = number_lines * avg_line_length

        # open our file
        with open(file_name, "r", encoding="utf-8") as f:

            # seek
            f.seek(0, 2)

            # get file size
            fsize = f.tell()

            # set pos @ last n chars
            # (buffer from above = number of lines * avg_line_length)
            f.seek(max(fsize - line_buffer, 0), 0)

            # read file til the end
            try:
                lines = f.readlines()

            except Exception as e:
                logger.warning(
                    f"Unable to read a line in the file:{file_name} - due to error: {e}"
                )

        # now we are done getting the lines, let's return it
        return lines

    @staticmethod
    def check_writeable(path: str):
        filename = os.path.join(path, "tempfile.txt")
        try:
            with open(filename, "w", encoding="utf-8"):
                pass
            os.remove(filename)

            logger.info(f"{filename} is writable")
            return True

        except Exception as e:
            logger.critical(f"Unable to write to {path} - Error: {e}")
            return False

    @staticmethod
    def check_root():
        if Helpers.is_os_windows():
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        return os.geteuid() == 0

    def ensure_logging_setup(self):
        log_file = os.path.join(os.path.curdir, "logs", "commander.log")
        session_log_file = os.path.join(os.path.curdir, "logs", "session.log")

        logger.info("Checking app directory writable")

        writeable = Helpers.check_writeable(self.root_dir)

        # if not writeable, let's bomb out
        if not writeable:
            logger.critical(f"Unable to write to {self.root_dir} directory!")
            sys.exit(1)

        # ensure the log directory is there
        try:
            with suppress(FileExistsError):
                os.makedirs(os.path.join(self.root_dir, "logs"))
        except Exception as e:
            Console.error(f"Failed to make logs directory with error: {e} ")

        # ensure the log file is there
        try:
            with open(log_file, "a", encoding="utf-8"):
                pass
        except Exception as e:
            Console.critical(f"Unable to open log file! {e}")
            sys.exit(1)

        # del any old session.lock file as this is a new session
        try:
            with contextlib.suppress(FileNotFoundError):
                os.remove(session_log_file)
        except Exception as e:
            Console.error(f"Deleting logs/session.log failed with error: {e}")

    @staticmethod
    def get_time_as_string():
        now = datetime.now()
        return now.strftime("%m/%d/%Y, %H:%M:%S")

    @staticmethod
    def calc_percent(source_path, dest_path):
        # calculates percentable of zip from drive. Not with compression.
        # (For backups and support logs)
        source_size = 0
        files_count = 0
        for path, _dirs, files in os.walk(source_path):
            for file in files:
                full_path = os.path.join(path, file)
                source_size += os.stat(full_path).st_size
                files_count += 1
        try:
            dest_size = os.path.getsize(str(dest_path))
            percent = round((dest_size / source_size) * 100, 1)
        except:
            percent = 0
        if percent >= 0:
            results = {"percent": percent, "total_files": files_count}
        else:
            results = {"percent": 0, "total_files": files_count}
        return results

    @staticmethod
    def check_file_exists(path: str):
        logger.debug(f"Looking for path: {path}")

        if os.path.exists(path) and os.path.isfile(path):
            logger.debug(f"Found path: {path}")
            return True
        return False

    @staticmethod
    def human_readable_file_size(num: int, suffix="B"):
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if abs(num) < 1024.0:
                # pylint: disable=consider-using-f-string
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
            # pylint: disable=consider-using-f-string
        return "%.1f%s%s" % (num, "Y", suffix)

    @staticmethod
    def check_path_exists(path: str):
        if not path:
            return False
        logger.debug(f"Looking for path: {path}")

        if os.path.exists(path):
            logger.debug(f"Found path: {path}")
            return True
        return False

    def get_gravatar_image(self, email):
        profile_url = "/static/assets/images/faces-clipart/pic-3.png"
        # http://en.gravatar.com/site/implement/images/#rating
        if self.get_setting("allow_nsfw_profile_pictures"):
            rating = "x"
        else:
            rating = "g"

        # Get grvatar hash for profile pictures
        if self.check_internet() and email != "default@example.com" and email:
            gravatar = libgravatar.Gravatar(libgravatar.sanitize_email(email))
            url = gravatar.get_image(
                size=80,
                default="404",
                force_default=False,
                rating=rating,
                filetype_extension=False,
                use_ssl=True,
            )  # + "?d=404"
            try:
                if requests.head(url).status_code != 404:
                    profile_url = url
            except Exception as e:
                logger.debug(f"Could not pull resource from Gravatar with error {e}")

        return profile_url

    @staticmethod
    def get_file_contents(path: str, lines=100):

        contents = ""

        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f.readlines()[-lines:]:
                        contents = contents + line

                return contents

            except Exception as e:
                logger.error(f"Unable to read file: {path}. \n Error: {e}")
                return False
        else:
            logger.error(
                f"Unable to read file: {path}. File not found, or isn't a file."
            )
            return False

    def create_session_file(self, ignore=False):

        if ignore and os.path.exists(self.session_file):
            os.remove(self.session_file)

        if os.path.exists(self.session_file):

            file_data = self.get_file_contents(self.session_file)
            try:
                data = json.loads(file_data)
                pid = data.get("pid")
                started = data.get("started")
                if psutil.pid_exists(pid):
                    Console.critical(
                        f"Another Crafty Controller agent seems to be running..."
                        f"\npid: {pid} \nstarted on: {started}"
                    )
                    logger.critical("Found running crafty process. Exiting.")
                    sys.exit(1)
                else:
                    logger.info(
                        "No process found for pid. Assuming "
                        "crafty crashed. Deleting stale session.lock"
                    )
                    os.remove(self.session_file)

            except Exception as e:
                logger.error(f"Failed to locate existing session.lock with error: {e} ")
                Console.error(
                    f"Failed to locate existing session.lock with error: {e} "
                )

                sys.exit(1)

        pid = os.getpid()
        now = datetime.now()

        session_data = {"pid": pid, "started": now.strftime("%d-%m-%Y, %H:%M:%S")}
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)

    # because this is a recursive function, we will return bytes,
    # and set human readable later
    @staticmethod
    def get_dir_size(path: str):
        total = 0
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                total += Helpers.get_dir_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
        return total

    @staticmethod
    def list_dir_by_date(path: str, reverse=False):
        return [
            str(p)
            for p in sorted(
                pathlib.Path(path).iterdir(), key=os.path.getmtime, reverse=reverse
            )
        ]

    @staticmethod
    def get_human_readable_files_sizes(paths: list):
        sizes = []
        for p in paths:
            sizes.append(
                {
                    "path": p,
                    "size": Helpers.human_readable_file_size(os.stat(p).st_size),
                }
            )
        return sizes

    @staticmethod
    def base64_encode_string(fun_str: str):
        s_bytes = str(fun_str).encode("utf-8")
        b64_bytes = base64.encodebytes(s_bytes)
        return b64_bytes.decode("utf-8")

    @staticmethod
    def base64_decode_string(fun_str: str):
        s_bytes = str(fun_str).encode("utf-8")
        b64_bytes = base64.decodebytes(s_bytes)
        return b64_bytes.decode("utf-8")

    @staticmethod
    def create_uuid():
        return str(uuid.uuid4())

    @staticmethod
    def ensure_dir_exists(path):
        """
        ensures a directory exists

        Checks for the existence of a directory, if the directory isn't there,
        this function creates the directory

        Args:
            path (string): the path you are checking for

        """

        try:
            os.makedirs(path)
            logger.debug(f"Created Directory : {path}")

        # directory already exists - non-blocking error
        except FileExistsError:
            pass
        except PermissionError as e:
            logger.critical(f"Check generated exception due to permssion error: {e}")

    def create_self_signed_cert(self, cert_dir=None):

        if cert_dir is None:
            cert_dir = os.path.join(self.config_dir, "web", "certs")

        # create a directory if needed
        Helpers.ensure_dir_exists(cert_dir)

        cert_file = os.path.join(cert_dir, "commander.cert.pem")
        key_file = os.path.join(cert_dir, "commander.key.pem")

        logger.info(f"SSL Cert File is set to: {cert_file}")
        logger.info(f"SSL Key File is set to: {key_file}")

        # don't create new files if we already have them.
        if Helpers.check_file_exists(cert_file) and Helpers.check_file_exists(key_file):
            logger.info("Cert and Key files already exists, not creating them.")
            return True

        Console.info("Generating a self signed SSL")
        logger.info("Generating a self signed SSL")

        # create a key pair
        logger.info("Generating a key pair. This might take a moment.")
        Console.info("Generating a key pair. This might take a moment.")
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "Michigan"
        cert.get_subject().L = "Kent County"
        cert.get_subject().O = "Crafty Controller"
        cert.get_subject().OU = "Server Ops"
        cert.get_subject().CN = gethostname()
        alt_names = ",".join(
            [
                f"DNS:{socket.gethostname()}",
                f"DNS:*.{socket.gethostname()}",
                "DNS:localhost",
                "DNS:*.localhost",
                "DNS:127.0.0.1",
            ]
        ).encode()
        subject_alt_names_ext = crypto.X509Extension(
            b"subjectAltName", False, alt_names
        )
        basic_constraints_ext = crypto.X509Extension(
            b"basicConstraints", True, b"CA:false"
        )
        cert.add_extensions([subject_alt_names_ext, basic_constraints_ext])
        cert.set_serial_number(secrets.randbelow(254) + 1)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.set_version(2)
        cert.sign(k, "sha256")

        with open(cert_file, "w", encoding="utf-8") as cert_file_handle:
            cert_file_handle.write(
                crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode()
            )

        with open(key_file, "w", encoding="utf-8") as key_file_handle:
            key_file_handle.write(
                crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode()
            )

    @staticmethod
    def random_string_generator(size=6, chars=string.ascii_uppercase + string.digits):
        """
        Example Usage
        random_generator() = G8sjO2
        random_generator(3, abcdef) = adf
        """
        return "".join(secrets.choice(chars) for x in range(size))

    @staticmethod
    def is_os_windows():
        return os.name == "nt"

    @staticmethod
    def wtol_path(w_path):
        l_path = w_path.replace("\\", "/")
        return l_path

    @staticmethod
    def ltow_path(l_path):
        w_path = l_path.replace("/", "\\")
        return w_path

    @staticmethod
    def get_os_understandable_path(path):
        return os.path.normpath(path)

    def find_default_password(self):
        default_file = os.path.join(self.root_dir, "default.json")
        data = {}

        if Helpers.check_file_exists(default_file):
            with open(default_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            del_json = self.get_setting("delete_default_json")

            if del_json:
                os.remove(default_file)

        return data

    @staticmethod
    def generate_tree(folder, output=""):
        dir_list = []
        unsorted_files = []
        file_list = os.listdir(folder)
        for item in file_list:
            if os.path.isdir(os.path.join(folder, item)):
                dir_list.append(item)
            elif str(item) != "crafty.sqlite":
                unsorted_files.append(item)
        file_list = sorted(dir_list, key=str.casefold) + sorted(
            unsorted_files, key=str.casefold
        )
        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if os.path.isdir(rel):
                output += f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i style="color: var(--info);" class="far fa-folder"></i>
                      <i style="color: var(--info);" class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </div><li>
                    \n"""
            else:
                if filename != "crafty_managed.txt":
                    output += f"""<li
                    class="d-block tree-ctx-item tree-file tree-item"
                    data-path="{dpath}"
                    data-name="{filename}"
                    onclick="clickOnFile(event)"><span style="margin-right: 6px;">
                    <i class="far fa-file"></i></span>{filename}</li>"""
        return output

    @staticmethod
    def generate_dir(folder, output=""):

        dir_list = []
        unsorted_files = []
        file_list = os.listdir(folder)
        for item in file_list:
            if os.path.isdir(os.path.join(folder, item)):
                dir_list.append(item)
            elif str(item) != "crafty.sqlite":
                unsorted_files.append(item)
        file_list = sorted(dir_list, key=str.casefold) + sorted(
            unsorted_files, key=str.casefold
        )
        output += f"""<ul class="tree-nested d-block" id="{folder}ul">"""
        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            dpath = os.path.join(folder, filename)
            rel = os.path.join(folder, raw_filename)
            if os.path.isdir(rel):
                output += f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i style="color: var(--info);" class="far fa-folder"></i>
                      <i style="color: var(--info);" class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </div><li>"""
            else:
                if filename != "crafty_managed.txt":
                    output += f"""<li
                    class="d-block tree-ctx-item tree-file tree-item"
                    data-path="{dpath}"
                    data-name="{filename}"
                    onclick="clickOnFile(event)"><span style="margin-right: 6px;">
                    <i class="far fa-file"></i></span>{filename}</li>"""
        output += "</ul>\n"
        return output

    @staticmethod
    def generate_zip_tree(folder, output=""):
        file_list = os.listdir(folder)
        file_list = sorted(file_list, key=str.casefold)
        output += f"""<ul class="tree-nested d-block" id="{folder}ul">"""
        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if os.path.isdir(rel):
                output += f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <input type="radio" name="root_path" value="{dpath}">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i style="color: var(--info);" class="far fa-folder"></i>
                      <i style="color: var(--info);" class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </input></div><li>
                    \n"""
        return output

    @staticmethod
    def generate_zip_dir(folder, output=""):
        file_list = os.listdir(folder)
        file_list = sorted(file_list, key=str.casefold)
        output += f"""<ul class="tree-nested d-block" id="{folder}ul">"""
        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if os.path.isdir(rel):
                output += f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <input type="radio" name="root_path" value="{dpath}">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i style="color: var(--info);" class="far fa-folder"></i>
                      <i style="color: var(--info);" class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </input></div><li>"""
        return output

    def unzip_server(self, zip_path, user_id):
        if Helpers.check_file_perms(zip_path):
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # extracts archive to temp directory
                zip_ref.extractall(temp_dir)
            if user_id:
                self.websocket_helper.broadcast_user(
                    user_id, "send_temp_path", {"path": temp_dir}
                )

    def backup_select(self, path, user_id):
        if user_id:
            self.websocket_helper.broadcast_user(
                user_id, "send_temp_path", {"path": path}
            )

    @staticmethod
    def unzip_backup_archive(backup_path, zip_name):
        zip_path = os.path.join(backup_path, zip_name)
        if Helpers.check_file_perms(zip_path):
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # extracts archive to temp directory
                zip_ref.extractall(temp_dir)
            return temp_dir
        return False

    @staticmethod
    def in_path(parent_path, child_path):
        # Smooth out relative path names, note: if you are concerned about
        # symbolic links, you should use os.path.realpath too
        parent_path = os.path.abspath(parent_path)
        child_path = os.path.abspath(child_path)

        # Compare the common path of the parent and child path with the
        # common path of just the parent path. Using the commonpath method
        # on just the parent path will regularise the path name in the same way
        # as the comparison that deals with both paths, removing any trailing
        # path separator
        return os.path.commonpath([parent_path]) == os.path.commonpath(
            [parent_path, child_path]
        )

    @staticmethod
    def download_file(executable_url, jar_path):
        try:
            response = requests.get(executable_url, timeout=5)
        except Exception as ex:
            logger.error("Could not download executable: %s", ex)
            return False
        if response.status_code != 200:
            logger.error("Unable to download file from %s", executable_url)
            return False

        try:
            with open(jar_path, "wb") as jar_file:
                jar_file.write(response.content)
        except Exception as e:
            logger.error("Unable to finish executable download. Error: %s", e)
            return False
        return True

    @staticmethod
    def remove_prefix(text, prefix):
        if text.startswith(prefix):
            return text[len(prefix) :]
        return text

    @staticmethod
    def get_lang_page(text) -> str:
        splitted = text.split("_")
        if len(splitted) != 2:
            return "en"
        lang, region = splitted
        if region == "EN":
            return "en"
        return lang + "-" + region

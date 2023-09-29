from contextlib import redirect_stderr
import os
import re
import shutil
import time
import datetime
import base64
import threading
import logging.config
import subprocess
import html
import urllib.request
import glob
import json

from zoneinfo import ZoneInfo

# TZLocal is set as a hidden import on win pipeline
from tzlocal import get_localzone
from tzlocal.utils import ZoneInfoNotFoundError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError, ConflictingIdError

from app.classes.minecraft.stats import Stats
from app.classes.minecraft.mc_ping import ping, ping_bedrock
from app.classes.models.servers import HelperServers, Servers
from app.classes.models.server_stats import HelperServerStats
from app.classes.models.management import HelpersManagement, HelpersWebhooks
from app.classes.models.users import HelperUsers
from app.classes.models.server_permissions import PermissionsServers
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.shared.file_helpers import FileHelpers
from app.classes.shared.null_writer import NullWriter
from app.classes.shared.websocket_manager import WebSocketManager
from app.classes.web.webhooks.webhook_factory import WebhookFactory

with redirect_stderr(NullWriter()):
    import psutil
    from psutil import NoSuchProcess

logger = logging.getLogger(__name__)


class ServerOutBuf:
    lines = {}

    def __init__(self, helper, proc, server_id):
        self.helper = helper
        self.proc = proc
        self.server_id = str(server_id)
        # Buffers text for virtual_terminal_lines config number of lines
        self.max_lines = self.helper.get_setting("virtual_terminal_lines")
        self.line_buffer = ""
        ServerOutBuf.lines[self.server_id] = []
        self.lsi = 0

    def process_byte(self, char):
        if char == os.linesep[self.lsi]:
            self.lsi += 1
        else:
            self.lsi = 0
            self.line_buffer += char

        if self.lsi >= len(os.linesep):
            self.lsi = 0
            ServerOutBuf.lines[self.server_id].append(self.line_buffer)

            self.new_line_handler(self.line_buffer)
            self.line_buffer = ""
            # Limit list length to self.max_lines:
            if len(ServerOutBuf.lines[self.server_id]) > self.max_lines:
                ServerOutBuf.lines[self.server_id].pop(0)

    def check(self):
        while True:
            if self.proc.poll() is None:
                char = self.proc.stdout.read(1).decode("utf-8", "ignore")
                # TODO: we may want to benchmark reading in blocks and userspace
                # processing it later, reads are kind of expensive as a syscall
                self.process_byte(char)
            else:
                flush = self.proc.stdout.read().decode("utf-8", "ignore")
                for char in flush:
                    self.process_byte(char)
                break

    def new_line_handler(self, new_line):
        new_line = re.sub("(\033\\[(0;)?[0-9]*[A-z]?(;[0-9])?m?)", " ", new_line)
        new_line = re.sub("[A-z]{2}\b\b", "", new_line)
        highlighted = self.helper.log_colors(html.escape(new_line))

        logger.debug("Broadcasting new virtual terminal line")

        # TODO: Do not send data to clients who do not have permission to view
        # this server's console
        if len(WebSocketManager().clients) > 0:
            WebSocketManager().broadcast_page_params(
                "/panel/server_detail",
                {"id": self.server_id},
                "vterm_new_line",
                {"line": highlighted + "<br />"},
            )


# **********************************************************************************
#                               Minecraft Server Class
# **********************************************************************************
class ServerInstance:
    server_object: Servers
    helper: Helpers
    file_helper: FileHelpers
    management_helper: HelpersManagement
    stats: Stats
    stats_helper: HelperServerStats

    def __init__(self, server_id, helper, management_helper, stats, file_helper):
        self.helper = helper
        self.file_helper = file_helper
        self.management_helper = management_helper
        # holders for our process
        self.process = None
        self.line = False
        self.start_time = None
        self.server_command = None
        self.server_path = None
        self.server_thread = None
        self.settings = None
        self.updating = False
        self.server_id = server_id
        self.jar_update_url = None
        self.name = None
        self.is_crashed = False
        self.restart_count = 0
        self.stats = stats
        self.server_object = HelperServers.get_server_obj(self.server_id)
        self.stats_helper = HelperServerStats(self.server_id)
        self.last_backup_failed = False
        try:
            with open(
                os.path.join(self.server_object.path, "db_stats", "players_cache.json"),
                "r",
                encoding="utf-8",
            ) as f:
                self.player_cache = list(json.load(f).values())
        except:
            self.player_cache = []
        try:
            self.tz = get_localzone()
        except ZoneInfoNotFoundError as e:
            logger.error(
                "Could not capture time zone from system. Falling back to Europe/London"
                f" error: {e}"
            )
            self.tz = ZoneInfo("Europe/London")
        self.server_scheduler = BackgroundScheduler(timezone=str(self.tz))
        self.dir_scheduler = BackgroundScheduler(timezone=str(self.tz))
        self.server_scheduler.start()
        self.dir_scheduler.start()
        self.start_dir_calc_task()
        self.backup_thread = threading.Thread(
            target=self.a_backup_server, daemon=True, name=f"backup_{self.name}"
        )
        self.is_backingup = False
        # Reset crash and update at initialization
        self.stats_helper.server_crash_reset()
        self.stats_helper.set_update(False)

    @staticmethod
    def callback(called_func):
        def wrapper(*args, **kwargs):
            res = None
            try:
                res = called_func(*args, **kwargs)
            finally:
                events = WebhookFactory.get_monitored_events()
                if called_func.__name__ in events:
                    server_webhooks = HelpersWebhooks.get_webhooks_by_server(
                        args[0].server_id, True
                    )
                    for swebhook in server_webhooks:
                        if called_func.__name__ in str(swebhook.trigger).split(","):
                            webhook = HelpersWebhooks.get_webhook_by_id(swebhook.id)
                            webhook_provider = WebhookFactory.create_provider(
                                webhook["webhook_type"]
                            )
                            if res is not False and swebhook.enabled:
                                webhook_provider.send(
                                    bot_name=webhook["bot_name"],
                                    server_name=args[0].name,
                                    title=webhook["name"],
                                    url=webhook["url"],
                                    message=webhook["body"],
                                    color=webhook["color"],
                                )
            return res

        return wrapper

    # **********************************************************************************
    #                               Minecraft Server Management
    # **********************************************************************************
    def update_server_instance(self):
        server_data: Servers = HelperServers.get_server_obj(self.server_id)
        self.server_path = server_data.path
        self.jar_update_url = server_data.executable_update_url
        self.name = server_data.server_name
        self.server_object = server_data
        self.stats_helper.select_database()
        self.reload_server_settings()

    def reload_server_settings(self):
        server_data = HelperServers.get_server_data_by_id(self.server_id)
        self.settings = server_data

    def do_server_setup(self, server_data_obj):
        server_id = server_data_obj["server_id"]
        server_name = server_data_obj["server_name"]
        auto_start = server_data_obj["auto_start"]

        logger.info(
            f"Creating Server object: {server_id} | "
            f"Server Name: {server_name} | "
            f"Auto Start: {auto_start}"
        )
        self.server_id = server_id
        self.name = server_name
        self.settings = server_data_obj

        self.record_server_stats()

        # build our server run command

        if server_data_obj["auto_start"]:
            delay = int(self.settings["auto_start_delay"])

            logger.info(f"Scheduling server {self.name} to start in {delay} seconds")
            Console.info(f"Scheduling server {self.name} to start in {delay} seconds")

            self.server_scheduler.add_job(
                self.run_scheduled_server,
                "interval",
                seconds=delay,
                id=str(self.server_id),
            )

    def run_scheduled_server(self):
        Console.info(f"Starting server ID: {self.server_id} - {self.name}")
        logger.info(f"Starting server ID: {self.server_id} - {self.name}")
        # Sets waiting start to false since we're attempting to start the server.
        self.stats_helper.set_waiting_start(False)
        self.run_threaded_server(None)

        # remove the scheduled job since it's ran
        return self.server_scheduler.remove_job(str(self.server_id))

    def run_threaded_server(self, user_id, forge_install=False):
        # start the server
        self.server_thread = threading.Thread(
            target=self.start_server,
            daemon=True,
            args=(
                user_id,
                forge_install,
            ),
            name=f"{self.server_id}_server_thread",
        )
        self.server_thread.start()

        # Register an shedule for polling server stats when running
        logger.info(f"Polling server statistics {self.name} every {5} seconds")
        Console.info(f"Polling server statistics {self.name} every {5} seconds")
        try:
            self.server_scheduler.add_job(
                self.realtime_stats,
                "interval",
                seconds=5,
                id="stats_" + str(self.server_id),
            )
        except:
            self.server_scheduler.remove_job("stats_" + str(self.server_id))
            self.server_scheduler.add_job(
                self.realtime_stats,
                "interval",
                seconds=5,
                id="stats_" + str(self.server_id),
            )
        logger.info(f"Saving server statistics {self.name} every {30} seconds")
        Console.info(f"Saving server statistics {self.name} every {30} seconds")
        try:
            self.server_scheduler.add_job(
                self.record_server_stats,
                "interval",
                seconds=30,
                id="save_stats_" + str(self.server_id),
            )
        except ConflictingIdError:
            self.server_scheduler.remove_job("save_stats_" + str(self.server_id))
            self.server_scheduler.add_job(
                self.record_server_stats,
                "interval",
                seconds=30,
                id="save_stats_" + str(self.server_id),
            )

    def setup_server_run_command(self):
        # configure the server
        server_exec_path = Helpers.get_os_understandable_path(
            self.settings["executable"]
        )
        self.server_command = Helpers.cmdparse(self.settings["execution_command"])
        if self.helper.is_os_windows() and self.server_command[0] == "java":
            logger.info(
                "Detected nebulous java in start command. "
                "Replacing with full java path."
            )
            oracle_path = shutil.which("java")
            if oracle_path:
                # Checks for Oracle Java. Only Oracle Java's helper will cause a re-exec
                if "/Oracle/Java/" in str(self.helper.wtol_path(oracle_path)):
                    logger.info(
                        "Oracle Java detected. Changing"
                        " start command to avoid re-exec."
                    )
                    which_java_raw = self.helper.which_java()
                    try:
                        java_path = which_java_raw + "\\bin\\java"
                    except TypeError:
                        logger.warning(
                            "Could not find java in the registry even though"
                            " Oracle java is installed."
                            " Re-exec expected, but we have no"
                            " other options. CPU stats will not work for process."
                        )
                        java_path = ""
                    if str(which_java_raw) != str(
                        self.helper.get_servers_root_dir
                    ) or str(self.helper.get_servers_root_dir) in str(which_java_raw):
                        if java_path != "":
                            self.server_command[0] = java_path
                    else:
                        logger.critcal(
                            "Possible attack detected. User attempted to exec "
                            "java binary from server directory."
                        )
                        return
        self.server_path = Helpers.get_os_understandable_path(self.settings["path"])

        # let's do some quick checking to make sure things actually exists
        full_path = os.path.join(self.server_path, server_exec_path)
        if not Helpers.check_file_exists(full_path):
            logger.critical(
                f"Server executable path: {full_path} does not seem to exist"
            )
            Console.critical(
                f"Server executable path: {full_path} does not seem to exist"
            )

        if not Helpers.check_path_exists(self.server_path):
            logger.critical(f"Server path: {self.server_path} does not seem to exits")
            Console.critical(f"Server path: {self.server_path} does not seem to exits")

        if not Helpers.check_writeable(self.server_path):
            logger.critical(f"Unable to write/access {self.server_path}")
            Console.critical(f"Unable to write/access {self.server_path}")

    @callback
    def start_server(self, user_id, forge_install=False):
        if not user_id:
            user_lang = self.helper.get_setting("language")
        else:
            user_lang = HelperUsers.get_user_lang_by_id(user_id)

        # Checks if user is currently attempting to move global server
        # dir
        if self.helper.dir_migration:
            WebSocketManager().broadcast_user(
                user_id,
                "send_start_error",
                {
                    "error": self.helper.translation.translate(
                        "error",
                        "migration",
                        user_lang,
                    )
                },
            )
            return False

        if self.stats_helper.get_import_status() and not forge_install:
            if user_id:
                WebSocketManager().broadcast_user(
                    user_id,
                    "send_start_error",
                    {
                        "error": self.helper.translation.translate(
                            "error", "not-downloaded", user_lang
                        )
                    },
                )
            return False

        logger.info(
            f"Start command detected. Reloading settings from DB for server {self.name}"
        )
        self.setup_server_run_command()
        # fail safe in case we try to start something already running
        if self.check_running():
            logger.error("Server is already running - Cancelling Startup")
            Console.error("Server is already running - Cancelling Startup")
            return False
        if self.check_update():
            logger.error("Server is updating. Terminating startup.")
            return False

        logger.info(f"Launching Server {self.name} with command {self.server_command}")
        Console.info(f"Launching Server {self.name} with command {self.server_command}")

        # Checks for eula. Creates one if none detected.
        # If EULA is detected and not set to true we offer to set it true.
        e_flag = False
        if Helpers.check_file_exists(os.path.join(self.settings["path"], "eula.txt")):
            with open(
                os.path.join(self.settings["path"], "eula.txt"), "r", encoding="utf-8"
            ) as f:
                line = f.readline().lower()
                e_flag = line in [
                    "eula=true",
                    "eula = true",
                    "eula= true",
                    "eula =true",
                ]
        # If this is a forge installer we're running we can bypass the eula checks.
        if forge_install is True:
            e_flag = True
        if not e_flag and self.settings["type"] == "minecraft-java":
            if user_id:
                WebSocketManager().broadcast_user(
                    user_id, "send_eula_bootbox", {"id": self.server_id}
                )
            else:
                logger.error(
                    "Autostart failed due to EULA being false. "
                    "Agree not sent due to auto start."
                )
            return False
        if Helpers.is_os_windows():
            logger.info("Windows Detected")
        else:
            logger.info("Unix Detected")

        logger.info(
            f"Starting server in {self.server_path} with command: {self.server_command}"
        )

        # checks to make sure file is openable (downloaded) and exists.
        try:
            with open(
                os.path.join(
                    self.server_path,
                    HelperServers.get_server_data_by_id(self.server_id)["executable"],
                ),
                "r",
                encoding="utf-8",
            ):
                # Can open the file
                pass

        except:
            if user_id:
                WebSocketManager().broadcast_user(
                    user_id,
                    "send_start_error",
                    {
                        "error": self.helper.translation.translate(
                            "error", "not-downloaded", user_lang
                        )
                    },
                )
            return

        if (
            not Helpers.is_os_windows()
            and HelperServers.get_server_type_by_id(self.server_id)
            == "minecraft-bedrock"
        ):
            logger.info(
                f"Bedrock and Unix detected for server {self.name}. "
                f"Switching to appropriate execution string"
            )
            my_env = os.environ
            my_env["LD_LIBRARY_PATH"] = self.server_path
            try:
                self.process = subprocess.Popen(
                    self.server_command,
                    cwd=self.server_path,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=my_env,
                )
            except Exception as ex:
                logger.error(
                    f"Server {self.name} failed to start with error code: {ex}"
                )
                if user_id:
                    WebSocketManager().broadcast_user(
                        user_id,
                        "send_start_error",
                        {
                            "error": self.helper.translation.translate(
                                "error", "start-error", user_lang
                            ).format(self.name, ex)
                        },
                    )
                if forge_install:
                    # Reset import status if failed while forge installing
                    self.stats_helper.finish_import()
                return False

        else:
            try:
                self.process = subprocess.Popen(
                    self.server_command,
                    cwd=self.server_path,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            except Exception as ex:
                # Checks for java on initial fail
                if not self.helper.detect_java():
                    if user_id:
                        WebSocketManager().broadcast_user(
                            user_id,
                            "send_start_error",
                            {
                                "error": self.helper.translation.translate(
                                    "error", "noJava", user_lang
                                ).format(self.name)
                            },
                        )
                    return False
                logger.error(
                    f"Server {self.name} failed to start with error code: {ex}"
                )
                if user_id:
                    WebSocketManager().broadcast_user(
                        user_id,
                        "send_start_error",
                        {
                            "error": self.helper.translation.translate(
                                "error", "start-error", user_lang
                            ).format(self.name, ex)
                        },
                    )
                if forge_install:
                    # Reset import status if failed while forge installing
                    self.stats_helper.finish_import()
                return False

        out_buf = ServerOutBuf(self.helper, self.process, self.server_id)

        logger.debug(f"Starting virtual terminal listener for server {self.name}")
        threading.Thread(
            target=out_buf.check, daemon=True, name=f"{self.server_id}_virtual_terminal"
        ).start()

        self.is_crashed = False
        self.stats_helper.server_crash_reset()

        self.start_time = str(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

        if self.process.poll() is None:
            logger.info(f"Server {self.name} running with PID {self.process.pid}")
            Console.info(f"Server {self.name} running with PID {self.process.pid}")
            self.is_crashed = False
            self.stats_helper.server_crash_reset()
            self.record_server_stats()
            check_internet_thread = threading.Thread(
                target=self.check_internet_thread,
                daemon=True,
                args=(
                    user_id,
                    user_lang,
                ),
                name=f"{self.name}_Internet",
            )
            check_internet_thread.start()
            # Checks if this is the servers first run.
            if self.stats_helper.get_first_run():
                self.stats_helper.set_first_run()
                loc_server_port = self.stats_helper.get_server_stats()["server_port"]
                # Sends port reminder message.
                WebSocketManager().broadcast_user(
                    user_id,
                    "send_start_error",
                    {
                        "error": self.helper.translation.translate(
                            "error", "portReminder", user_lang
                        ).format(self.name, loc_server_port)
                    },
                )
                server_users = PermissionsServers.get_server_user_list(self.server_id)
                for user in server_users:
                    if user != user_id:
                        WebSocketManager().broadcast_user(user, "send_start_reload", {})
            else:
                server_users = PermissionsServers.get_server_user_list(self.server_id)
                for user in server_users:
                    WebSocketManager().broadcast_user(user, "send_start_reload", {})
        else:
            logger.warning(
                f"Server PID {self.process.pid} died right after starting "
                f"- is this a server config issue?"
            )
            Console.critical(
                f"Server PID {self.process.pid} died right after starting "
                f"- is this a server config issue?"
            )

        if self.settings["crash_detection"]:
            logger.info(
                f"Server {self.name} has crash detection enabled "
                f"- starting watcher task"
            )
            Console.info(
                f"Server {self.name} has crash detection enabled "
                f"- starting watcher task"
            )

            self.server_scheduler.add_job(
                self.detect_crash, "interval", seconds=30, id=f"c_{self.server_id}"
            )

        # If this is a forge install we'll call the watcher to do the things
        if forge_install:
            self.forge_install_watcher()

    def check_internet_thread(self, user_id, user_lang):
        if user_id:
            if not Helpers.check_internet():
                WebSocketManager().broadcast_user(
                    user_id,
                    "send_start_error",
                    {
                        "error": self.helper.translation.translate(
                            "error", "internet", user_lang
                        )
                    },
                )

    def forge_install_watcher(self):
        # Enter for install if that parameter is true
        while True:
            # We'll watch the process
            if self.process.poll() is None:
                # IF process still has not exited we'll keep looping
                time.sleep(5)
                Console.debug("Installing Forge...")
            else:
                # Process has exited. Lets do some work to setup the new
                # run command.
                # Let's grab the server object we're going to update.
                server_obj: Servers = HelperServers.get_server_obj(self.server_id)

                # The forge install is done so we can delete that install file.
                os.remove(os.path.join(server_obj.path, server_obj.executable))

                # We need to grab the exact forge version number.
                # We know we can find it here in the run.sh/bat script.
                try:
                    # Getting the forge version from the executable command
                    version = re.findall(
                        r"forge-([0-9\.]+)((?:)|(?:-([0-9\.]+)-[a-zA-Z]+)).jar",
                        server_obj.execution_command,
                    )
                    version_param = version[0][0].split(".")
                    version_major = int(version_param[0])
                    version_minor = int(version_param[1])

                    # Checking which version we are with
                    if version_major <= 1 and version_minor < 17:
                        # OLD VERSION < 1.17

                        # Retrieving the executable jar filename
                        file_path = glob.glob(
                            f"{server_obj.path}/forge-{version[0][0]}*.jar"
                        )[0]
                        file_name = re.findall(
                            r"(forge[-0-9.]+.jar)",
                            file_path,
                        )[0]

                        # Let's set the proper server executable
                        server_obj.executable = os.path.join(file_name)

                        # Get memory values
                        memory_values = re.findall(
                            r"-Xms([A-Z0-9\.]+) -Xmx([A-Z0-9\.]+)",
                            server_obj.execution_command,
                        )

                        # Now lets set up the new run command.
                        # This is based off the run.sh/bat that
                        # Forge uses in 1.17 and <
                        execution_command = (
                            f"java -Xms{memory_values[0][0]} -Xmx{memory_values[0][1]}"
                            f' -jar "{file_name}" nogui'
                        )
                        server_obj.execution_command = execution_command
                        Console.debug("SUCCESS! Forge install completed")

                    else:
                        # NEW VERSION >= 1.17

                        run_file_path = ""
                        if self.helper.is_os_windows():
                            run_file_path = os.path.join(server_obj.path, "run.bat")
                        else:
                            run_file_path = os.path.join(server_obj.path, "run.sh")

                        if Helpers.check_file_perms(run_file_path) and os.path.isfile(
                            run_file_path
                        ):
                            run_file = open(run_file_path, "r", encoding="utf-8")
                            run_file_text = run_file.read()
                        else:
                            Console.error(
                                "ERROR ! Forge install can't read the scripts files."
                                " Aborting ..."
                            )
                            return

                        # We get the server command parameters from forge script
                        server_command = re.findall(
                            r"java @([a-zA-Z0-9_\.]+)"
                            r" @([a-z.\/\-]+)([0-9.\-]+)"
                            r"\/\b([a-z_0-9]+\.txt)\b( .{2,4})?",
                            run_file_text,
                        )[0]

                        version = server_command[2]
                        executable_path = f"{server_command[1]}{server_command[2]}/"

                        # Let's set the proper server executable
                        server_obj.executable = os.path.join(
                            f"{executable_path}forge-{version}-server.jar"
                        )
                        # Now lets set up the new run command.
                        # This is based off the run.sh/bat that
                        # Forge uses in 1.17 and <
                        execution_command = (
                            f"java @{server_command[0]}"
                            f" @{executable_path}{server_command[3]} nogui"
                            f" {server_command[4]}"
                        )
                        server_obj.execution_command = execution_command
                        Console.debug("SUCCESS! Forge install completed")
                except:
                    logger.debug("Could not find run file.")
                    # TODO Use regex to get version and rebuild simple execution

                # We'll update the server with the new information now.
                HelperServers.update_server(server_obj)
                self.stats_helper.finish_import()
                server_users = PermissionsServers.get_server_user_list(self.server_id)

                for user in server_users:
                    WebSocketManager().broadcast_user(user, "send_start_reload", {})
                break

    def stop_crash_detection(self):
        # This is only used if the crash detection settings change
        # while the server is running.
        if self.check_running():
            logger.info(f"Detected crash detection shut off for server {self.name}")
            try:
                self.server_scheduler.remove_job("c_" + str(self.server_id))
            except:
                logger.error(
                    f"Removing crash watcher for server {self.name} failed. "
                    f"Assuming it was never started."
                )

    def start_crash_detection(self):
        # This is only used if the crash detection settings change
        # while the server is running.
        if self.check_running():
            logger.info(
                f"Server {self.name} has crash detection enabled "
                f"- starting watcher task"
            )
            Console.info(
                f"Server {self.name} has crash detection enabled "
                "- starting watcher task"
            )
            try:
                self.server_scheduler.add_job(
                    self.detect_crash, "interval", seconds=30, id=f"c_{self.server_id}"
                )
            except:
                logger.info(f"Job with id c_{self.server_id} already running...")

    def stop_threaded_server(self):
        self.stop_server()

        if self.server_thread:
            self.server_thread.join()

    @callback
    def stop_server(self):
        running = self.check_running()
        if not running:
            logger.info(f"Can't stop server {self.name} if it's not running")
            Console.info(f"Can't stop server {self.name} if it's not running")
            return
        if self.settings["crash_detection"]:
            # remove crash detection watcher
            logger.info(f"Removing crash watcher for server {self.name}")
            try:
                self.server_scheduler.remove_job("c_" + str(self.server_id))
            except:
                logger.error(
                    f"Removing crash watcher for server {self.name} failed. "
                    f"Assuming it was never started."
                )
        if self.settings["stop_command"]:
            self.send_command(self.settings["stop_command"])
            self.write_player_cache()
        else:
            # windows will need to be handled separately for Ctrl+C
            self.process.terminate()
        i = 0

        # caching the name and pid number
        server_name = self.name
        server_pid = self.process.pid
        self.shutdown_timeout = self.settings["shutdown_timeout"]

        while running:
            i += 1
            ttk = int(self.shutdown_timeout - (i * 2))
            if i <= self.shutdown_timeout / 2:
                logstr = (
                    f"Server {server_name} is still running "
                    "- waiting 2s to see if it stops"
                    f"({ttk} "
                    f"seconds until force close)"
                )
                logger.info(logstr)
                Console.info(logstr)
            running = self.check_running()
            time.sleep(2)

            # if we haven't closed in 60 seconds, let's just slam down on the PID
            if i >= round(self.shutdown_timeout / 2, 0):
                logger.info(
                    f"Server {server_name} is still running - Forcing the process down"
                )
                Console.info(
                    f"Server {server_name} is still running - Forcing the process down"
                )
                self.kill()

        logger.info(f"Stopped Server {server_name} with PID {server_pid}")
        Console.info(f"Stopped Server {server_name} with PID {server_pid}")

        # massive resetting of variables
        self.cleanup_server_object()
        server_users = PermissionsServers.get_server_user_list(self.server_id)

        try:
            # remove the stats polling job since server is stopped
            self.server_scheduler.remove_job("stats_" + str(self.server_id))
        except JobLookupError as e:
            logger.error(
                f"Could not remove job with id stats_{self.server_id} due"
                + f" to error: {e}"
            )
        self.record_server_stats()

        for user in server_users:
            WebSocketManager().broadcast_user(user, "send_start_reload", {})

    def restart_threaded_server(self, user_id):
        bu_conf = HelpersManagement.get_backup_config(self.server_id)
        if self.is_backingup and bu_conf["shutdown"]:
            logger.info(
                "Restart command detected. Supressing - server has"
                " backup shutdown enabled and server is currently backing up."
            )
            return
        # if not already running, let's just start
        if not self.check_running():
            self.run_threaded_server(user_id)
        else:
            self.stop_threaded_server()
            time.sleep(2)
            self.run_threaded_server(user_id)

    def cleanup_server_object(self):
        self.start_time = None
        self.restart_count = 0
        self.is_crashed = False
        self.updating = False
        self.process = None

    def check_running(self):
        # if process is None, we never tried to start
        if self.process is None:
            return False
        poll = self.process.poll()
        if poll is None:
            return True
        self.last_rc = poll
        return False

    @callback
    def send_command(self, command):
        if not self.check_running() and command.lower() != "start":
            logger.warning(f'Server not running, unable to send command "{command}"')
            return False
        Console.info(f"COMMAND TIME: {command}")
        logger.debug(f"Sending command {command} to server")

        # send it
        self.process.stdin.write(f"{command}\n".encode("utf-8"))
        self.process.stdin.flush()
        return True

    @callback
    def crash_detected(self, name):
        # clear the old scheduled watcher task
        self.server_scheduler.remove_job(f"c_{self.server_id}")
        # remove the stats polling job since server is stopped
        self.server_scheduler.remove_job("stats_" + str(self.server_id))

        # the server crashed, or isn't found - so let's reset things.
        logger.warning(
            f"The server {name} seems to have vanished unexpectedly, did it crash?"
        )

        if self.settings["crash_detection"]:
            logger.warning(
                f"The server {name} has crashed and will be restarted. "
                f"Restarting server"
            )
            Console.critical(
                f"The server {name} has crashed and will be restarted. "
                f"Restarting server"
            )

            self.run_threaded_server(None)
            return True
        logger.critical(
            f"The server {name} has crashed, "
            f"crash detection is disabled and it will not be restarted"
        )
        Console.critical(
            f"The server {name} has crashed, "
            f"crash detection is disabled and it will not be restarted"
        )
        return False

    @callback
    def kill(self):
        logger.info(f"Terminating server {self.server_id} and all child processes")
        try:
            process = psutil.Process(self.process.pid)
        except NoSuchProcess:
            logger.info(f"Cannot kill {self.process.pid} as we cannot find that pid.")
            return
        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes
            logger.info(f"Sending SIGKILL to server {proc.name}")
            proc.kill()
        # kill the main process we are after
        logger.info("Sending SIGKILL to parent")
        try:
            self.server_scheduler.remove_job("stats_" + str(self.server_id))
        except JobLookupError as e:
            logger.error(
                f"Could not remove job with id stats_{self.server_id} due"
                + f" to error: {e}"
            )
        self.process.kill()

    def get_start_time(self):
        return self.start_time if self.check_running() else False

    def get_pid(self):
        return self.process.pid if self.process is not None else None

    def detect_crash(self):
        logger.info(f"Detecting possible crash for server: {self.name} ")

        running = self.check_running()

        # if all is okay, we just exit out
        if running:
            return
        # check the exit code -- This could be a fix for /stop
        if str(self.process.returncode) in self.settings["ignored_exits"].split(","):
            logger.warning(
                f"Process {self.process.pid} exited with code "
                f"{self.process.returncode}. This is considered a clean exit"
                f" supressing crash handling."
            )
            # cancel the watcher task
            self.server_scheduler.remove_job("c_" + str(self.server_id))
            self.server_scheduler.remove_job("stats_" + str(self.server_id))
            return

        self.stats_helper.sever_crashed()
        # if we haven't tried to restart more 3 or more times
        if self.restart_count <= 3:
            # start the server if needed
            server_restarted = self.crash_detected(self.name)

            if server_restarted:
                # add to the restart count
                self.restart_count = self.restart_count + 1

        # we have tried to restart 4 times...
        elif self.restart_count == 4:
            logger.critical(
                f"Server {self.name} has been restarted {self.restart_count}"
                f" times. It has crashed, not restarting."
            )
            Console.critical(
                f"Server {self.name} has been restarted {self.restart_count}"
                f" times. It has crashed, not restarting."
            )

            self.restart_count = 0
            self.is_crashed = True
            self.stats_helper.sever_crashed()

            # cancel the watcher task
            self.server_scheduler.remove_job("c_" + str(self.server_id))

    def remove_watcher_thread(self):
        logger.info("Removing old crash detection watcher thread")
        Console.info("Removing old crash detection watcher thread")
        self.server_scheduler.remove_job("c_" + str(self.server_id))

    def agree_eula(self, user_id):
        eula_file = os.path.join(self.server_path, "eula.txt")
        with open(eula_file, "w", encoding="utf-8") as f:
            f.write("eula=true")
        self.run_threaded_server(user_id)

    @callback
    def backup_server(self):
        if self.settings["backup_path"] == "":
            logger.critical("Backup path is None. Canceling Backup!")
            return
        backup_thread = threading.Thread(
            target=self.a_backup_server, daemon=True, name=f"backup_{self.name}"
        )
        logger.info(
            f"Starting Backup Thread for server {self.settings['server_name']}."
        )
        if self.server_path is None:
            self.server_path = Helpers.get_os_understandable_path(self.settings["path"])
            logger.info(
                "Backup Thread - Local server path not defined. "
                "Setting local server path variable."
            )
        # checks if the backup thread is currently alive for this server
        if not self.is_backingup:
            try:
                backup_thread.start()
                self.is_backingup = True
            except Exception as ex:
                logger.error(f"Failed to start backup: {ex}")
                return False
        else:
            logger.error(
                f"Backup is already being processed for server "
                f"{self.settings['server_name']}. Canceling backup request"
            )
            return False
        logger.info(f"Backup Thread started for server {self.settings['server_name']}.")

    def a_backup_server(self):
        was_server_running = None
        logger.info(f"Starting server {self.name} (ID {self.server_id}) backup")
        server_users = PermissionsServers.get_server_user_list(self.server_id)
        for user in server_users:
            WebSocketManager().broadcast_user(
                user,
                "notification",
                self.helper.translation.translate(
                    "notify", "backupStarted", HelperUsers.get_user_lang_by_id(user)
                ).format(self.name),
            )
        time.sleep(3)
        conf = HelpersManagement.get_backup_config(self.server_id)
        if conf["before"]:
            if self.check_running():
                logger.debug(
                    "Found running server and send command option. Sending command"
                )
                self.send_command(conf["before"])

        if conf["shutdown"]:
            if conf["before"]:
                # pause to let people read message.
                time.sleep(5)
            logger.info(
                "Found shutdown preference. Delaying"
                + "backup start. Shutting down server."
            )
            if self.check_running():
                self.stop_server()
                was_server_running = True

        self.helper.ensure_dir_exists(self.settings["backup_path"])
        try:
            backup_filename = (
                f"{self.settings['backup_path']}/"
                f"{datetime.datetime.now().astimezone(self.tz).strftime('%Y-%m-%d_%H-%M-%S')}"  # pylint: disable=line-too-long
            )
            logger.info(
                f"Creating backup of server '{self.settings['server_name']}'"
                f" (ID#{self.server_id}, path={self.server_path}) "
                f"at '{backup_filename}'"
            )
            excluded_dirs = HelpersManagement.get_excluded_backup_dirs(self.server_id)
            server_dir = Helpers.get_os_understandable_path(self.settings["path"])
            if conf["compress"]:
                logger.debug(
                    "Found compress backup to be true. Calling compressed archive"
                )
                self.file_helper.make_compressed_backup(
                    Helpers.get_os_understandable_path(backup_filename),
                    server_dir,
                    excluded_dirs,
                    self.server_id,
                )
            else:
                logger.debug(
                    "Found compress backup to be false. Calling NON-compressed archive"
                )
                self.file_helper.make_backup(
                    Helpers.get_os_understandable_path(backup_filename),
                    server_dir,
                    excluded_dirs,
                    self.server_id,
                )

            while (
                len(self.list_backups()) > conf["max_backups"]
                and conf["max_backups"] > 0
            ):
                backup_list = self.list_backups()
                oldfile = backup_list[0]
                oldfile_path = f"{conf['backup_path']}/{oldfile['path']}"
                logger.info(f"Removing old backup '{oldfile['path']}'")
                os.remove(Helpers.get_os_understandable_path(oldfile_path))

            self.is_backingup = False
            logger.info(f"Backup of server: {self.name} completed")
            results = {"percent": 100, "total_files": 0, "current_file": 0}
            if len(WebSocketManager().clients) > 0:
                WebSocketManager().broadcast_page_params(
                    "/panel/server_detail",
                    {"id": str(self.server_id)},
                    "backup_status",
                    results,
                )
            server_users = PermissionsServers.get_server_user_list(self.server_id)
            for user in server_users:
                WebSocketManager().broadcast_user(
                    user,
                    "notification",
                    self.helper.translation.translate(
                        "notify",
                        "backupComplete",
                        HelperUsers.get_user_lang_by_id(user),
                    ).format(self.name),
                )
            if was_server_running:
                logger.info(
                    "Backup complete. User had shutdown preference. Starting server."
                )
                self.run_threaded_server(HelperUsers.get_user_id_by_name("system"))
            time.sleep(3)
            self.last_backup_failed = False
            if conf["after"]:
                if self.check_running():
                    logger.debug(
                        "Found running server and send command option. Sending command"
                    )
                    self.send_command(conf["after"])
            # pause to let people read message.
            time.sleep(5)
        except:
            logger.exception(
                f"Failed to create backup of server {self.name} (ID {self.server_id})"
            )
            results = {"percent": 100, "total_files": 0, "current_file": 0}
            if len(WebSocketManager().clients) > 0:
                WebSocketManager().broadcast_page_params(
                    "/panel/server_detail",
                    {"id": str(self.server_id)},
                    "backup_status",
                    results,
                )
            self.is_backingup = False
            if was_server_running:
                logger.info(
                    "Backup complete. User had shutdown preference. Starting server."
                )
                self.run_threaded_server(HelperUsers.get_user_id_by_name("system"))
            self.last_backup_failed = True

    def backup_status(self, source_path, dest_path):
        results = Helpers.calc_percent(source_path, dest_path)
        self.backup_stats = results
        if len(WebSocketManager().clients) > 0:
            WebSocketManager().broadcast_page_params(
                "/panel/server_detail",
                {"id": str(self.server_id)},
                "backup_status",
                results,
            )

    def last_backup_status(self):
        return self.last_backup_failed

    def send_backup_status(self):
        try:
            return self.backup_stats
        except:
            return {"percent": 0, "total_files": 0}

    def list_backups(self):
        if not self.settings["backup_path"]:
            logger.info(
                f"Error putting backup file list for server with ID: {self.server_id}"
            )
            return []
        if not Helpers.check_path_exists(
            Helpers.get_os_understandable_path(self.settings["backup_path"])
        ):
            return []
        files = Helpers.get_human_readable_files_sizes(
            Helpers.list_dir_by_date(
                Helpers.get_os_understandable_path(self.settings["backup_path"])
            )
        )
        return [
            {
                "path": os.path.relpath(
                    f["path"],
                    start=Helpers.get_os_understandable_path(
                        self.settings["backup_path"]
                    ),
                ),
                "size": f["size"],
            }
            for f in files
            if f["path"].endswith(".zip")
        ]

    @callback
    def jar_update(self):
        self.stats_helper.set_update(True)
        update_thread = threading.Thread(
            target=self.a_jar_update, daemon=True, name=f"exe_update_{self.name}"
        )
        update_thread.start()

    def write_player_cache(self):
        write_json = {}
        for item in self.player_cache:
            write_json[item["name"]] = item
        with open(
            os.path.join(self.server_path, "db_stats", "players_cache.json"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(write_json, indent=4))
            logger.info("Cache file refreshed")

    def cache_players(self):
        server_players = self.get_server_players()
        for p in self.player_cache[:]:
            if p["status"] == "Online" and p["name"] not in server_players:
                p["status"] = "Offline"
                p["last_seen"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            elif p["name"] in server_players:
                self.player_cache.remove(p)
        for player in server_players:
            if player == "Anonymous Player":
                # Skip Anonymous Player
                continue
            if player in self.player_cache:
                self.player_cache.remove(player)
            self.player_cache.append(
                {
                    "name": player,
                    "status": "Online",
                    "last_seen": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
            )

    def check_update(self):
        return self.stats_helper.get_server_stats()["updating"]

    def a_jar_update(self):
        server_users = PermissionsServers.get_server_user_list(self.server_id)
        was_started = "-1"
        self.backup_server()
        # checks if server is running. Calls shutdown if it is running.
        if self.check_running():
            was_started = True
            logger.info(
                f"Server with PID {self.process.pid} is running. "
                f"Sending shutdown command"
            )
            self.stop_threaded_server()
        else:
            was_started = False
        if len(WebSocketManager().clients) > 0:
            # There are clients
            self.check_update()
            message = (
                '<a data-id="' + str(self.server_id) + '" class=""> UPDATING...</i></a>'
            )
        for user in server_users:
            WebSocketManager().broadcast_user_page(
                "/panel/server_detail",
                user,
                "update_button_status",
                {
                    "isUpdating": self.check_update(),
                    "server_id": self.server_id,
                    "wasRunning": was_started,
                    "string": message,
                },
            )
        backup_dir = os.path.join(
            Helpers.get_os_understandable_path(self.settings["path"]),
            "crafty_executable_backups",
        )
        # checks if backup directory already exists
        if os.path.isdir(backup_dir):
            backup_executable = os.path.join(backup_dir, self.settings["executable"])
        else:
            logger.info(
                f"Executable backup directory not found for Server: {self.name}."
                f" Creating one."
            )
            os.mkdir(backup_dir)
            backup_executable = os.path.join(backup_dir, self.settings["executable"])

        if len(os.listdir(backup_dir)) > 0:
            # removes old backup
            logger.info(f"Old backups found for server: {self.name}. Removing...")
            for item in os.listdir(backup_dir):
                os.remove(os.path.join(backup_dir, item))
            logger.info(f"Old backups removed for server: {self.name}.")
        else:
            logger.info(f"No old backups found for server: {self.name}")

        current_executable = os.path.join(
            Helpers.get_os_understandable_path(self.settings["path"]),
            self.settings["executable"],
        )

        try:
            # copies to backup dir
            FileHelpers.copy_file(current_executable, backup_executable)
        except FileNotFoundError:
            logger.error("Could not create backup of jarfile. File not found.")

        # wait for backup
        while self.is_backingup:
            time.sleep(10)

        # check if backup was successful
        if self.last_backup_failed:
            for user in server_users:
                WebSocketManager().broadcast_user(
                    user,
                    "notification",
                    "Backup failed for " + self.name + ". canceling update.",
                )
            return False

        # lets download the files
        if HelperServers.get_server_type_by_id(self.server_id) != "minecraft-bedrock":
            # boolean returns true for false for success
            downloaded = Helpers.download_file(
                self.settings["executable_update_url"], current_executable
            )
        else:
            # downloads zip from remote url
            try:
                bedrock_url = Helpers.get_latest_bedrock_url()
                if bedrock_url.lower().startswith("https"):
                    urllib.request.urlretrieve(
                        bedrock_url,
                        os.path.join(self.settings["path"], "bedrock_server.zip"),
                    )

                unzip_path = os.path.join(self.settings["path"], "bedrock_server.zip")
                unzip_path = self.helper.wtol_path(unzip_path)
                # unzips archive that was downloaded.
                FileHelpers.unzip_file(unzip_path, server_update=True)
                # adjusts permissions for execution if os is not windows
                if not self.helper.is_os_windows():
                    os.chmod(
                        os.path.join(self.settings["path"], "bedrock_server"), 0o0744
                    )

                # we'll delete the zip we downloaded now
                os.remove(os.path.join(self.settings["path"], "bedrock_server.zip"))
                downloaded = True
            except Exception as e:
                logger.critical(
                    f"Failed to download bedrock executable for update \n{e}"
                )
                downloaded = False

        if downloaded:
            logger.info("Executable updated successfully. Starting Server")

            self.stats_helper.set_update(False)
            if len(WebSocketManager().clients) > 0:
                # There are clients
                self.check_update()
                for user in server_users:
                    WebSocketManager().broadcast_user(
                        user,
                        "notification",
                        "Executable update finished for " + self.name,
                    )
                # sleep so first notif can completely run
                time.sleep(3)
            for user in server_users:
                WebSocketManager().broadcast_user_page(
                    "/panel/server_detail",
                    user,
                    "update_button_status",
                    {
                        "isUpdating": self.check_update(),
                        "server_id": self.server_id,
                        "wasRunning": was_started,
                    },
                )
                WebSocketManager().broadcast_user_page(
                    user, "/panel/dashboard", "send_start_reload", {}
                )
                WebSocketManager().broadcast_user(
                    user,
                    "notification",
                    "Executable update finished for " + self.name,
                )

            self.management_helper.add_to_audit_log_raw(
                "Alert",
                "-1",
                self.server_id,
                "Executable update finished for " + self.name,
                self.settings["server_ip"],
            )
            if was_started:
                self.run_threaded_server(HelperUsers.get_user_id_by_name("system"))
        else:
            for user in server_users:
                WebSocketManager().broadcast_user(
                    user,
                    "notification",
                    "Executable update failed for "
                    + self.name
                    + ". Check log file for details.",
                )
            logger.error("Executable download failed.")
            self.stats_helper.set_update(False)
        for user in server_users:
            WebSocketManager().broadcast_user(user, "remove_spinner", {})

    def start_dir_calc_task(self):
        server_dt = HelperServers.get_server_data_by_id(self.server_id)
        self.server_size = self.stats.get_server_dir_size(server_dt["path"])
        self.dir_scheduler.add_job(
            self.calc_dir_size,
            "interval",
            minutes=self.helper.get_setting("dir_size_poll_freq_minutes"),
            id=str(self.server_id) + "_dir_poll",
        )
        self.dir_scheduler.add_job(
            self.cache_players,
            "interval",
            seconds=5,
            id=str(self.server_id) + "_players_poll",
        )

    def calc_dir_size(self):
        server_dt = HelperServers.get_server_data_by_id(self.server_id)
        self.server_size = self.stats.get_server_dir_size(server_dt["path"])

    # **********************************************************************************
    #                               Minecraft Servers Statistics
    # **********************************************************************************

    def realtime_stats(self):
        # only get stats if clients are connected.
        # no point in burning cpu
        if len(WebSocketManager().clients) > 0:
            total_players = 0
            max_players = 0
            servers_ping = []
            raw_ping_result = []
            raw_ping_result = self.get_raw_server_stats(self.server_id)

            if f"{raw_ping_result.get('icon')}" == "b''":
                raw_ping_result["icon"] = False

            servers_ping.append(
                {
                    "id": raw_ping_result.get("id"),
                    "started": raw_ping_result.get("started"),
                    "running": raw_ping_result.get("running"),
                    "cpu": raw_ping_result.get("cpu"),
                    "mem": raw_ping_result.get("mem"),
                    "mem_percent": raw_ping_result.get("mem_percent"),
                    "world_name": raw_ping_result.get("world_name"),
                    "world_size": raw_ping_result.get("world_size"),
                    "server_port": raw_ping_result.get("server_port"),
                    "int_ping_results": raw_ping_result.get("int_ping_results"),
                    "online": raw_ping_result.get("online"),
                    "max": raw_ping_result.get("max"),
                    "players": raw_ping_result.get("players"),
                    "desc": raw_ping_result.get("desc"),
                    "version": raw_ping_result.get("version"),
                    "icon": raw_ping_result.get("icon"),
                    "crashed": self.is_crashed,
                }
            )

            WebSocketManager().broadcast_page_params(
                "/panel/server_detail",
                {"id": str(self.server_id)},
                "update_server_details",
                {
                    "id": raw_ping_result.get("id"),
                    "started": raw_ping_result.get("started"),
                    "running": raw_ping_result.get("running"),
                    "cpu": raw_ping_result.get("cpu"),
                    "mem": raw_ping_result.get("mem"),
                    "mem_percent": raw_ping_result.get("mem_percent"),
                    "world_name": raw_ping_result.get("world_name"),
                    "world_size": raw_ping_result.get("world_size"),
                    "server_port": raw_ping_result.get("server_port"),
                    "int_ping_results": raw_ping_result.get("int_ping_results"),
                    "online": raw_ping_result.get("online"),
                    "max": raw_ping_result.get("max"),
                    "players": raw_ping_result.get("players"),
                    "desc": raw_ping_result.get("desc"),
                    "version": raw_ping_result.get("version"),
                    "icon": raw_ping_result.get("icon"),
                    "crashed": self.is_crashed,
                    "created": datetime.datetime.now().strftime("%Y/%m/%d, %H:%M:%S"),
                    "players_cache": self.player_cache,
                },
            )
            total_players += int(raw_ping_result.get("online"))
            max_players += int(raw_ping_result.get("max"))

            # self.record_server_stats()

            if len(servers_ping) > 0:
                try:
                    WebSocketManager().broadcast_page(
                        "/panel/dashboard", "update_server_status", servers_ping
                    )
                except:
                    Console.critical("Can't broadcast server status to websocket")

    def get_servers_stats(self):
        server_stats = {}

        logger.info("Getting Stats for Server " + self.name + " ...")

        server_id = self.server_id
        server = HelperServers.get_server_data_by_id(server_id)

        logger.debug(f"Getting stats for server: {server_id}")

        # get our server object, settings and data dictionaries
        self.reload_server_settings()

        # process stats
        p_stats = Stats._try_get_process_stats(self.process, self.check_running())
        internal_ip = server["server_ip"]
        server_port = server["server_port"]
        server_name = server.get("server_name", f"ID#{server_id}")

        logger.debug(f"Pinging server '{server}' on {internal_ip}:{server_port}")
        if HelperServers.get_server_type_by_id(server_id) == "minecraft-bedrock":
            int_mc_ping = ping_bedrock(internal_ip, int(server_port))
        else:
            try:
                int_mc_ping = ping(internal_ip, int(server_port))
            except:
                int_mc_ping = False

        int_data = False
        ping_data = {}

        # if we got a good ping return, let's parse it
        if int_mc_ping:
            int_data = True
            if (
                HelperServers.get_server_type_by_id(server["server_id"])
                == "minecraft-bedrock"
            ):
                ping_data = Stats.parse_server_raknet_ping(int_mc_ping)
            else:
                ping_data = Stats.parse_server_ping(int_mc_ping)
        # Makes sure we only show stats when a server is online
        # otherwise people have gotten confused.
        if self.check_running():
            server_stats = {
                "id": server_id,
                "started": self.get_start_time(),
                "running": self.check_running(),
                "cpu": p_stats.get("cpu_usage", 0),
                "mem": p_stats.get("memory_usage", 0),
                "mem_percent": p_stats.get("mem_percentage", 0),
                "world_name": server_name,
                "world_size": self.server_size,
                "server_port": server_port,
                "int_ping_results": int_data,
                "online": ping_data.get("online", False),
                "max": ping_data.get("max", False),
                "players": ping_data.get("players", False),
                "desc": ping_data.get("server_description", False),
                "version": ping_data.get("server_version", False),
                "icon": ping_data.get("server_icon"),
            }
        else:
            server_stats = {
                "id": server_id,
                "started": self.get_start_time(),
                "running": self.check_running(),
                "cpu": p_stats.get("cpu_usage", 0),
                "mem": p_stats.get("memory_usage", 0),
                "mem_percent": p_stats.get("mem_percentage", 0),
                "world_name": server_name,
                "world_size": self.server_size,
                "server_port": server_port,
                "int_ping_results": int_data,
                "online": False,
                "max": False,
                "players": False,
                "desc": False,
                "version": False,
                "icon": None,
            }

        return server_stats

    def get_server_players(self):
        server = HelperServers.get_server_data_by_id(self.server_id)

        logger.info(f"Getting players for server {server}")

        internal_ip = server["server_ip"]
        server_port = server["server_port"]

        logger.debug(f"Pinging {internal_ip} on port {server_port}")
        if HelperServers.get_server_type_by_id(self.server_id) != "minecraft-bedrock":
            int_mc_ping = ping(internal_ip, int(server_port))

            ping_data = {}

            # if we got a good ping return, let's parse it
            if int_mc_ping:
                ping_data = Stats.parse_server_ping(int_mc_ping)
                return ping_data["players"]
        return []

    def get_raw_server_stats(self, server_id):
        try:
            server = HelperServers.get_server_obj(server_id)
        except:
            return {
                "id": server_id,
                "started": False,
                "running": False,
                "cpu": 0,
                "mem": 0,
                "mem_percent": 0,
                "world_name": None,
                "world_size": None,
                "server_port": None,
                "int_ping_results": False,
                "online": False,
                "max": False,
                "players": False,
                "desc": False,
                "version": False,
                "icon": False,
            }

        server_stats = {}
        if not server:
            return {}
        server_dt = HelperServers.get_server_data_by_id(server_id)

        logger.debug(f"Getting stats for server: {server_id}")

        # get our server object, settings and data dictionaries
        self.reload_server_settings()

        # world data
        server_name = server_dt["server_name"]

        # process stats
        p_stats = Stats._try_get_process_stats(self.process, self.check_running())

        internal_ip = server_dt["server_ip"]
        server_port = server_dt["server_port"]

        logger.debug(f"Pinging server '{self.name}' on {internal_ip}:{server_port}")
        if HelperServers.get_server_type_by_id(server_id) == "minecraft-bedrock":
            int_mc_ping = ping_bedrock(internal_ip, int(server_port))
        else:
            int_mc_ping = ping(internal_ip, int(server_port))

        int_data = False
        ping_data = {}
        # Makes sure we only show stats when a server is online
        # otherwise people have gotten confused.
        if self.check_running():
            # if we got a good ping return, let's parse it
            if HelperServers.get_server_type_by_id(server_id) != "minecraft-bedrock":
                if int_mc_ping:
                    int_data = True
                    ping_data = Stats.parse_server_ping(int_mc_ping)

                server_stats = {
                    "id": server_id,
                    "started": self.get_start_time(),
                    "running": self.check_running(),
                    "cpu": p_stats.get("cpu_usage", 0),
                    "mem": p_stats.get("memory_usage", 0),
                    "mem_percent": p_stats.get("mem_percentage", 0),
                    "world_name": server_name,
                    "world_size": self.server_size,
                    "server_port": server_port,
                    "int_ping_results": int_data,
                    "online": ping_data.get("online", False),
                    "max": ping_data.get("max", False),
                    "players": ping_data.get("players", False),
                    "desc": ping_data.get("server_description", False),
                    "version": ping_data.get("server_version", False),
                    "icon": ping_data.get("server_icon", False),
                }

            else:
                if int_mc_ping:
                    int_data = True
                    ping_data = Stats.parse_server_raknet_ping(int_mc_ping)
                    try:
                        server_icon = base64.encodebytes(ping_data["icon"])
                    except Exception as ex:
                        server_icon = False
                        logger.info(f"Unable to read the server icon : {ex}")

                    server_stats = {
                        "id": server_id,
                        "started": self.get_start_time(),
                        "running": self.check_running(),
                        "cpu": p_stats.get("cpu_usage", 0),
                        "mem": p_stats.get("memory_usage", 0),
                        "mem_percent": p_stats.get("mem_percentage", 0),
                        "world_name": server_name,
                        "world_size": self.server_size,
                        "server_port": server_port,
                        "int_ping_results": int_data,
                        "online": ping_data["online"],
                        "max": ping_data["max"],
                        "players": [],
                        "desc": ping_data["server_description"],
                        "version": ping_data["server_version"],
                        "icon": server_icon,
                    }
                else:
                    server_stats = {
                        "id": server_id,
                        "started": self.get_start_time(),
                        "running": self.check_running(),
                        "cpu": p_stats.get("cpu_usage", 0),
                        "mem": p_stats.get("memory_usage", 0),
                        "mem_percent": p_stats.get("mem_percentage", 0),
                        "world_name": server_name,
                        "world_size": self.server_size,
                        "server_port": server_port,
                        "int_ping_results": int_data,
                        "online": False,
                        "max": False,
                        "players": False,
                        "desc": False,
                        "version": False,
                        "icon": False,
                    }
        else:
            server_stats = {
                "id": server_id,
                "started": self.get_start_time(),
                "running": self.check_running(),
                "cpu": p_stats.get("cpu_usage", 0),
                "mem": p_stats.get("memory_usage", 0),
                "mem_percent": p_stats.get("mem_percentage", 0),
                "world_name": server_name,
                "world_size": self.server_size,
                "server_port": server_port,
                "int_ping_results": int_data,
                "online": False,
                "max": False,
                "players": False,
                "desc": False,
                "version": False,
            }

        return server_stats

    def record_server_stats(self):
        server_stats = self.get_servers_stats()
        self.stats_helper.insert_server_stats(server_stats)

        # delete old data
        max_age = self.helper.get_setting("history_max_age")
        now = datetime.datetime.now()
        minimum_to_exist = now - datetime.timedelta(days=max_age)

        self.stats_helper.remove_old_stats(minimum_to_exist)

    def get_server_history(self):
        history = self.stats_helper.get_history_stats(self.server_id, 1)
        return history

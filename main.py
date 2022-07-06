import os
import sys
import json
from threading import Thread
import time
import argparse
import logging.config
import signal
import peewee
from app.classes.shared.file_helpers import FileHelpers

from app.classes.shared.import3 import Import3
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.models.users import HelperUsers

console = Console()
helper = Helpers()
if helper.check_root():
    Console.critical(
        "Root detected. Root/Admin access denied. "
        "Run Crafty again with non-elevated permissions."
    )
    time.sleep(5)
    Console.critical("Crafty shutting down. Root/Admin access denied.")
    sys.exit(0)
# pylint: disable=wrong-import-position
try:
    from app.classes.models.base_model import database_proxy
    from app.classes.shared.main_models import DatabaseBuilder
    from app.classes.shared.tasks import TasksManager
    from app.classes.shared.main_controller import Controller
    from app.classes.shared.migration import MigrationManager
    from app.classes.shared.command import MainPrompt
except ModuleNotFoundError as err:
    helper.auto_installer_fix(err)


def do_intro():
    logger.info("***** Crafty Controller Started *****")

    version = helper.get_version_string()

    intro = f"""
    {'/' * 75}
    #{("Welcome to Crafty Controller - v." + version).center(73, " ")}#
    {'/' * 75}
    #{"Server Manager / Web Portal for your Minecraft server".center(73, " ")}#
    #{"Homepage: www.craftycontrol.com".center(73, " ")}#
    {'/' * 75}
    """

    Console.magenta(intro)


def setup_logging(debug=True):
    logging_config_file = os.path.join(os.path.curdir, "app", "config", "logging.json")

    if os.path.exists(logging_config_file):
        # open our logging config file
        with open(logging_config_file, "rt", encoding="utf-8") as f:
            logging_config = json.load(f)
            if debug:
                logging_config["loggers"][""]["level"] = "DEBUG"

            logging.config.dictConfig(logging_config)

    else:
        logging.basicConfig(level=logging.DEBUG)
        logging.warning(f"Unable to read logging config from {logging_config_file}")
        Console.critical(f"Unable to read logging config from {logging_config_file}")


# Our Main Starter
if __name__ == "__main__":
    parser = argparse.ArgumentParser("Crafty Controller - A Server Management System")

    parser.add_argument(
        "-i", "--ignore", action="store_true", help="Ignore session.lock files"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Sets logging level to debug."
    )

    parser.add_argument(
        "-d",
        "--daemon",
        action="store_true",
        help="Runs Crafty in daemon mode (no prompt)",
    )

    args = parser.parse_args()

    helper.ensure_logging_setup()

    setup_logging(debug=args.verbose)

    # setting up the logger object
    logger = logging.getLogger(__name__)
    Console.cyan(f"Logging set to: {logger.level}")
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.INFO)

    # print our pretty start message
    do_intro()

    # our session file, helps prevent multiple controller agents on the same machine.
    helper.create_session_file(ignore=args.ignore)

    # start the database
    database = peewee.SqliteDatabase(
        helper.db_path, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
    )
    database_proxy.initialize(database)

    migration_manager = MigrationManager(database, helper)
    migration_manager.up()  # Automatically runs migrations

    # do our installer stuff
    user_helper = HelperUsers(database, helper)
    installer = DatabaseBuilder(database, helper, user_helper)
    FRESH_INSTALL = installer.is_fresh_install()

    if FRESH_INSTALL:
        Console.debug("Fresh install detected")
        Console.warning(
            f"We have detected a fresh install. Please be sure to forward "
            f"Crafty's port, {helper.get_setting('https_port')}, "
            f"through your router/firewall if you would like to be able "
            f"to access Crafty remotely."
        )
        installer.default_settings()
    else:
        Console.debug("Existing install detected")
    file_helper = FileHelpers(helper)
    # now the tables are created, we can load the tasks_manager and server controller
    controller = Controller(database, helper, file_helper)
    import3 = Import3(helper, controller)
    tasks_manager = TasksManager(helper, controller)
    tasks_manager.start_webserver()

    def signal_handler(signum, _frame):
        if not args.daemon:
            print()  # for newline after prompt
        signame = signal.Signals(signum).name
        logger.info(f"Recieved signal {signame} [{signum}], stopping Crafty...")
        Console.info(f"Recieved signal {signame} [{signum}], stopping Crafty...")
        tasks_manager._main_graceful_exit()
        crafty_prompt.universal_exit()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # init servers
    logger.info("Initializing all servers defined")
    Console.info("Initializing all servers defined")
    controller.servers.init_all_servers()

    def tasks_starter():
        # start stats logging
        tasks_manager.start_stats_recording()

        # once the controller is up and stats are logging, we can kick off
        # the scheduler officially
        tasks_manager.start_scheduler()

        # refresh our cache and schedule for every 12 hoursour cache refresh
        # for serverjars.com
        tasks_manager.serverjar_cache_refresher()

    tasks_starter_thread = Thread(target=tasks_starter, name="tasks_starter")

    def internet_check():
        print()
        logger.info("Checking Internet. This may take a minute.")
        Console.info("Checking Internet. This may take a minute.")

        if not helper.check_internet():
            logger.warning(
                "We have detected the machine running Crafty has no "
                "connection to the internet. Client connections to "
                "the server may be limited."
            )
            Console.warning(
                "We have detected the machine running Crafty has no "
                "connection to the internet. Client connections to "
                "the server may be limited."
            )

    internet_check_thread = Thread(target=internet_check, name="internet_check")

    def controller_setup():
        if not controller.check_system_user():
            controller.add_system_user()

        project_root = os.path.dirname(__file__)
        controller.set_project_root(project_root)
        controller.clear_unexecuted_commands()
        controller.clear_support_status()

    crafty_prompt = MainPrompt(
        helper, tasks_manager, migration_manager, controller, import3
    )

    controller_setup_thread = Thread(target=controller_setup, name="controller_setup")

    def setup_starter():
        if not args.daemon:
            time.sleep(0.01)  # Wait for the prompt to start
            print()  # Make a newline after the prompt so logs are on an empty line
        else:
            time.sleep(0.01)  # Wait for the daemon info message

        Console.info("Setting up Crafty's internal components...")

        # Start the setup threads
        tasks_starter_thread.start()
        internet_check_thread.start()
        controller_setup_thread.start()

        # Wait for the setup threads to finish
        tasks_starter_thread.join()
        internet_check_thread.join()
        controller_setup_thread.join()

        Console.info("Crafty has fully started and is now ready for use!")
        crafty_prompt.prompt = f"Crafty Controller v{helper.get_version_string()} > "
        try:
            logger.info("Removing old temp dirs")
            FileHelpers.del_dirs(os.path.join(controller.project_root, "temp"))
        except:
            logger.info("Did not find old temp dir.")
        os.mkdir(os.path.join(controller.project_root, "temp"))

        if not args.daemon:
            # Put the prompt under the cursor
            crafty_prompt.print_prompt()

    Thread(target=setup_starter, name="setup_starter").start()

    if not args.daemon:
        # Start the Crafty prompt
        crafty_prompt.cmdloop()
    else:
        Console.info("Crafty started in daemon mode, no shell will be printed")
        print()
        while True:
            if tasks_manager.get_main_thread_run_status():
                break
            time.sleep(1)
        tasks_manager._main_graceful_exit()
        crafty_prompt.universal_exit()

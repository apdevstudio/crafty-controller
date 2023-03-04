import datetime
import logging
import sys
import locale

logger = logging.getLogger(__name__)
locale.setlocale(locale.LC_ALL, "")  # Get the locale from the environment

try:
    from colorama import init
    from termcolor import colored

except ModuleNotFoundError as ex:
    logger.critical(f"Import Error: Unable to load {ex.name} module", exc_info=True)
    print(f"Import Error: Unable to load {ex.name} module")
    from app.classes.shared.installer import installer

    installer.do_install()


class Console:
    level = ""

    def __init__(self):
        if "colorama" in sys.modules:
            init()

    @staticmethod
    def get_fmt_date_time():
        # This will use the local date (%x) and time (%X) formatting
        return datetime.datetime.now().strftime("%x %X")

    @staticmethod
    def do_print(message, color):
        if "termcolor" in sys.modules or "colorama" in sys.modules:
            print(colored(message, color))
        else:
            print(message)

    @staticmethod
    def magenta(message):
        Console.do_print(message, "magenta")

    @staticmethod
    def cyan(message):
        Console.do_print(message, "cyan")

    @staticmethod
    def yellow(message):
        Console.do_print(message, "yellow")

    @staticmethod
    def red(message):
        Console.do_print(message, "red")

    @staticmethod
    def green(message):
        Console.do_print(message, "green")

    @staticmethod
    def white(message):
        Console.do_print(message, "white")

    @staticmethod
    def debug(message):
        if Console.level == "debug":
            date_time = Console.get_fmt_date_time()
            Console.magenta(f"[+] Crafty: {date_time} - DEBUG:\t{message}")

    @staticmethod
    def info(message):
        date_time = Console.get_fmt_date_time()
        Console.white(f"[+] Crafty: {date_time} - INFO:\t{message}")

    @staticmethod
    def warning(message):
        date_time = Console.get_fmt_date_time()
        Console.cyan(f"[+] Crafty: {date_time} - WARNING:\t{message}")

    @staticmethod
    def error(message):
        date_time = Console.get_fmt_date_time()
        Console.yellow(f"[+] Crafty: {date_time} - ERROR:\t{message}")

    @staticmethod
    def critical(message):
        date_time = Console.get_fmt_date_time()
        Console.red(f"[+] Crafty: {date_time} - CRITICAL:\t{message}")

    @staticmethod
    def help(message):
        date_time = Console.get_fmt_date_time()
        Console.green(f"[+] Crafty: {date_time} - HELP:\t{message}")
